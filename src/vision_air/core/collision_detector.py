import time
import numpy as np

class CollisionDetector:
    def __init__(self, threshold=0.015, debounce_s=0.2):
        self.threshold = threshold
        self.debounce_s = debounce_s
        self.last_z = None
        self.last_time = None
        self.last_hit_time = 0
        
        # Buffers for smoothing dZ/dt
        self.velocity_buffer = []
        self.buffer_size = 3

    def update(self, z):
        curr_time = time.time()
        hit_triggered = False
        
        if self.last_z is not None and self.last_time is not None:
            dt = curr_time - self.last_time
            if dt > 0:
                # Velocity (dZ/dt)
                # MediaPipe Z increases as finger moves away from camera (towards desk)
                vel = (z - self.last_z) / dt
                
                self.velocity_buffer.append(vel)
                if len(self.velocity_buffer) > self.buffer_size:
                    self.velocity_buffer.pop(0)
                
                avg_vel = np.mean(self.velocity_buffer)
                
                # Collision Logic:
                # 1. We must be moving 'down' (positive velocity)
                # 2. Velocity must 'peak' and then drop suddenly
                # For simplicity, we detect when velocity exceeds a threshold 
                # and then a 'reversal' happens soon after.
                # BETTER: Just check if z is 'low enough' and velocity is dropping.
                # Since we don't have absolute height, we look for 'spikes' in velocity.
                
                if avg_vel < -self.threshold: # Sudden movement 'up' after a stay/down
                    # This is likely the 'bounce' off the desk
                    if curr_time - self.last_hit_time > self.debounce_s:
                        hit_triggered = True
                        self.last_hit_time = curr_time
                        
        self.last_z = z
        self.last_time = curr_time
        return hit_triggered

class MultiFingerCollisionManager:
    def __init__(self):
        # We track all 21 landmarks or just the 5 fingertips (4, 8, 12, 16, 20)
        self.detectors = {i: CollisionDetector() for i in [4, 8, 12, 16, 20]}

    def check_collisions(self, hand_landmarks):
        hits = []
        for idx, detector in self.detectors.items():
            landmark = hand_landmarks.landmark[idx]
            if detector.update(landmark.z):
                hits.append((idx, landmark.x, landmark.y))
        return hits


class FingerTapDetector:
    """
    Detects a quick fingertip down/up impulse from relative MediaPipe Z.

    The sign of MediaPipe Z can feel inverted depending on camera setup, so this
    detector uses distance from an adaptive hover baseline instead of assuming a
    fixed "down" direction.
    """
    def __init__(
        self,
        name,
        trigger_depth=0.08, # Lowered from 0.10
        start_depth=0.04,   # Lowered from 0.06
        release_depth=0.05, # Raised from 0.035 for easier trigger
        min_velocity=0.30,  # Lowered from 0.45
        max_xy_velocity=1200.0,
        min_duration_s=0.035,
        max_duration_s=0.42,
        debounce_s=0.20,    # Slightly faster re-trigger
        signal_alpha=0.85, # Less smoothing = lower latency
        baseline_alpha=0.015, # Slower baseline drift
    ):
        self.name = name
        self.trigger_depth = trigger_depth
        self.start_depth = start_depth
        self.release_depth = release_depth
        self.min_velocity = min_velocity
        self.max_xy_velocity = max_xy_velocity
        self.min_duration_s = min_duration_s
        self.max_duration_s = max_duration_s
        self.debounce_s = debounce_s
        self.signal_alpha = signal_alpha
        self.baseline_alpha = baseline_alpha

        self.baseline = None
        self.smoothed = None
        self.prev_smoothed = None
        self.prev_time = None
        self.prev_xy = None
        self.state = "idle"
        self.start_time = None
        self.start_xy = None
        self.peak_depth = 0.0
        self.peak_velocity = 0.0
        self.last_tap_time = 0.0
        self.depth = 0.0
        self.velocity = 0.0
        self.xy_vel = 0.0

    def update(self, z_signal, xy=None, timestamp=None, palm_scale=1.0, contact_confirm=True):
        timestamp = timestamp or time.monotonic()
        event = False

        if self.smoothed is None:
            self.smoothed = z_signal
            self.prev_smoothed = z_signal
            self.baseline = z_signal
            self.prev_time = timestamp
            self.prev_xy = xy
            return False

        dt = max(timestamp - self.prev_time, 1e-4)
        
        # 1. Update XY velocity for motion rejection
        self.xy_vel = 0.0
        if xy and self.prev_xy:
            dist = np.linalg.norm(np.array(xy) - np.array(self.prev_xy))
            self.xy_vel = dist / dt

        # 2. Smooth Z Signal
        self.smoothed = self.signal_alpha * z_signal + (1 - self.signal_alpha) * self.smoothed
        self.velocity = (self.smoothed - self.prev_smoothed) / dt
        
        # 3. Handle Baseline Smoothing with LOCKING
        # If we are in 'candidate' state, we stop updating the baseline for better release detection
        if self.state == "idle":
            self.baseline = (
                self.baseline_alpha * self.smoothed
                + (1 - self.baseline_alpha) * self.baseline
            )
        
        self.depth = abs(self.smoothed - self.baseline)

        # 4. State Machine
        if self.state == "idle":
            # REJECTION: Too fast horizontal movement
            if self.xy_vel > self.max_xy_velocity:
                pass
            # TRIGGER: Deep enough and fast enough
            elif (
                timestamp - self.last_tap_time > self.debounce_s
                and self.depth >= self.start_depth
                and abs(self.velocity) >= self.min_velocity
            ):
                self.state = "candidate"
                self.start_time = timestamp
                self.start_xy = xy
                self.peak_depth = self.depth
                self.peak_velocity = abs(self.velocity)
        else:
            duration = timestamp - self.start_time
            self.peak_depth = max(self.peak_depth, self.depth)
            self.peak_velocity = max(self.peak_velocity, abs(self.velocity))

            # ABORT: Motion too long or too much horizontal drift
            drift = 0.0
            if xy and self.start_xy:
                drift = np.linalg.norm(np.array(xy) - np.array(self.start_xy))

            if duration > self.max_duration_s or drift > (180.0 * palm_scale): # Drift limit
                self.reset_candidate()
            # RELEASE: Reached trigger depth and returned to near baseline
            elif (
                duration >= self.min_duration_s
                and self.peak_depth >= self.trigger_depth
                and self.depth <= self.release_depth
                and contact_confirm # ZERO TOLERANCE: Front camera must see contact
            ):
                event = True
                self.last_tap_time = timestamp
                self.reset_candidate()
                # Heavy re-anchor baseline after successful tap
                self.baseline = self.smoothed

        self.prev_smoothed = self.smoothed
        self.prev_time = timestamp
        self.prev_xy = xy
        return event

    def reset_candidate(self):
        self.state = "idle"
        self.start_time = None
        self.start_xy = None
        self.peak_depth = 0.0
        self.peak_velocity = 0.0

    def reset(self):
        self.baseline = None
        self.smoothed = None
        self.prev_smoothed = None
        self.prev_time = None
        self.reset_candidate()
        self.depth = 0.0
        self.velocity = 0.0

    def debug(self):
        return {
            "state": self.state,
            "depth": self.depth,
            "velocity": self.velocity,
            "xy_vel": self.xy_vel,
            "peak": self.peak_depth,
            "z": self.smoothed,
        }


class RightHandTapManager:
    def __init__(self):
        self.detectors = {
            "index": {
                "tip": 8,
                "mcp": 5,
                "button": "left",
                "detector": FingerTapDetector("index"),
            },
            "middle": {
                "tip": 12,
                "mcp": 9,
                "button": "right",
                "detector": FingerTapDetector("middle"),
            },
        }
        self.last_debug = {}

    def update(self, hand, engine, frame_shape, front_results=None):
        timestamp = time.monotonic()
        landmarks = hand["landmarks"]
        palm_scale = self._palm_scale(landmarks)
        events = []
        self.last_debug = {}
        
        # 0. Flatten front results for easier association
        all_front_tips = []
        if front_results:
            for hand_data in front_results:
                for tip_idx, data in hand_data.items():
                    all_front_tips.append(data)

        for finger, spec in self.detectors.items():
            tip = landmarks[spec["tip"]]
            mcp = landmarks[spec["mcp"]]
            z_signal = (tip.z - mcp.z) / palm_scale

            point = engine.warp_point(tip.x, tip.y, frame_shape[1], frame_shape[0])
            point_xy = (float(point[0]), float(point[1]))
            detector = spec["detector"]
            
            # 1. Zero-Tolerance Fusion: Find matching finger in front view
            # We match by normalized X coordinate.
            contact_confirm = True # Fallback if front cam is off
            if all_front_tips:
                best_match = None
                min_dx = 0.15 # Max normalized X difference allowed for association
                for f_tip in all_front_tips:
                    dx = abs(f_tip['x'] - tip.x)
                    if dx < min_dx:
                        min_dx = dx
                        best_match = f_tip
                
                if best_match:
                    contact_confirm = best_match['is_touching']
                else:
                    contact_confirm = False # Front view is ON but doesn't see this finger -> NO TOUCH

            if detector.update(z_signal, point_xy, timestamp, palm_scale, contact_confirm):
                events.append({
                    "finger": finger,
                    "button": spec["button"],
                    "point": point_xy,
                })

            self.last_debug[finger] = detector.debug()

        return events

    def reset(self):
        for spec in self.detectors.values():
            spec["detector"].reset()
        self.last_debug = {}

    def has_active_candidate(self):
        return any(
            spec["detector"].state != "idle"
            for spec in self.detectors.values()
        )

    def debug_text(self):
        parts = []
        for finger in ("index", "middle"):
            data = self.last_debug.get(finger)
            if not data:
                continue
            parts.append(
                f"{finger[0].upper()}:{data['state'][0]} "
                f"d={data['depth']:.2f} v={data['velocity']:.1f} xv={data['xy_vel']:.0f}"
            )
        return "Tap " + " | ".join(parts) if parts else "Tap: no right hand"

    def _palm_scale(self, landmarks):
        wrist = landmarks[0]
        index_mcp = landmarks[5]
        scale = np.linalg.norm(np.array([
            index_mcp.x - wrist.x,
            index_mcp.y - wrist.y,
        ]))
        return max(scale, 1e-3)
