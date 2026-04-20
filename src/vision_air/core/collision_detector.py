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
