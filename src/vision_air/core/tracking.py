import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import numpy as np
import os
import time
from ..utils.filters import OneEuroFilter
from ..utils.config import ConfigManager

class LandmarkCompat:
    """Compatibility wrapper to mimic the Legacy API structure."""
    def __init__(self, landmarks):
        self.landmark = landmarks

    def __getitem__(self, index):
        return self.landmark[index]

    def __iter__(self):
        return iter(self.landmark)

    def __len__(self):
        return len(self.landmark)





class TrackingEngine:
    """
    Tracking Engine using the modern MediaPipe Tasks API.
    HARDENED: Explicitly uses CPU delegate to avoid Windows Insider driver crashes.
    """
    def __init__(self, config_manager=None):
        self.config = config_manager or ConfigManager()
        self.config.load()
        
        # Path to the .task model
        model_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "assets", "models", "hand_landmarker.task")
        if not os.path.exists(model_path):
            # Fallback for alternative location
            model_path_alt = os.path.join(os.getcwd(), "assets", "models", "hand_landmarker.task")
            if os.path.exists(model_path_alt):
                model_path = model_path_alt
            else:
                raise FileNotFoundError(f"Model file not found at {model_path}. Please run the downloader utility.")

        # Tasks API Configuration - HARDENED: Explicitly use CPU delegate
        base_options = python.BaseOptions(
            model_asset_path=model_path,
            delegate=python.BaseOptions.Delegate.CPU 
        )
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=2,
            min_hand_detection_confidence=0.7,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5,
            running_mode=vision.RunningMode.VIDEO
        )
        self.landmarker = vision.HandLandmarker.create_from_options(options)
        
        self.filters = {
            'x': OneEuroFilter(30, min_cutoff=0.04, beta=0.15), # Precise and responsive
            'y': OneEuroFilter(30, min_cutoff=0.04, beta=0.15),
            'z': OneEuroFilter(30, min_cutoff=0.5, beta=0.00)
        }
        self.start_time = time.monotonic()
        self.last_timestamp_ms = 0

    def warp_point_with_status(self, x_norm, y_norm, img_w, img_h):
        px, py = x_norm * img_w, y_norm * img_h
        src_pt = np.array([[[px, py]]], dtype=np.float32)
        dst_pt = cv2.perspectiveTransform(src_pt, self.config.homography_matrix)
        x, y = self.apply_axis_correction(*dst_pt[0][0])
        desk_w, desk_h = self.config.desk_dims
        margin = 80
        in_bounds = -margin <= x <= desk_w + margin and -margin <= y <= desk_h + margin
        return np.array([np.clip(x, 0, desk_w), np.clip(y, 0, desk_h)], dtype=np.float32), in_bounds

    def warp_point(self, x_norm, y_norm, img_w, img_h):
        point, _ = self.warp_point_with_status(x_norm, y_norm, img_w, img_h)
        return point

    def apply_axis_correction(self, x, y):
        desk_w, desk_h = self.config.desk_dims
        correction = self.config.axis_correction

        if correction.get("swap_xy", False):
            x, y = (y / desk_h) * desk_w, (x / desk_w) * desk_h
        if correction.get("invert_x", False):
            x = desk_w - x
        if correction.get("invert_y", False):
            y = desk_h - y

        return np.array([x, y], dtype=np.float32)

    def next_timestamp_ms(self):
        timestamp_ms = int((time.monotonic() - self.start_time) * 1000)
        if timestamp_ms <= self.last_timestamp_ms:
            timestamp_ms = self.last_timestamp_ms + 1
        self.last_timestamp_ms = timestamp_ms
        return timestamp_ms



    def finger_is_extended(self, landmarks, mcp_idx, pip_idx, tip_idx):
        wrist = landmarks[0]
        pip = landmarks[pip_idx]
        tip = landmarks[tip_idx]

        wrist_to_pip = np.linalg.norm(np.array([pip.x - wrist.x, pip.y - wrist.y]))
        wrist_to_tip = np.linalg.norm(np.array([tip.x - wrist.x, tip.y - wrist.y]))
        if wrist_to_pip <= 1e-6:
            return False

        return wrist_to_tip > wrist_to_pip * 1.08

    def classify_fingers(self, landmarks):
        return {
            "index": self.finger_is_extended(landmarks, 5, 6, 8),
            "middle": self.finger_is_extended(landmarks, 9, 10, 12),
            "ring": self.finger_is_extended(landmarks, 13, 14, 16),
            "pinky": self.finger_is_extended(landmarks, 17, 18, 20),
        }

    def is_mouse_pose(self, finger_states):
        # Normal mouse pose: index extended, ring/pinky folded. Middle may be up/down.
        return (
            finger_states["index"]
            and not finger_states["ring"]
            and not finger_states["pinky"]
        )

    def process_frame(self, frame):
        h, w, _ = frame.shape
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        
        results = self.landmarker.detect_for_video(mp_image, self.next_timestamp_ms())
        
        tracked_data = []
        
        if results.hand_landmarks:
            for hand_index, hand_landmarks in enumerate(results.hand_landmarks[:2]):
                handedness = "Unknown"
                handedness_score = 0.0
                if results.handedness and hand_index < len(results.handedness) and results.handedness[hand_index]:
                    top_category = results.handedness[hand_index][0]
                    handedness = top_category.category_name
                    handedness_score = top_category.score

                itip = hand_landmarks[8]
                point, in_bounds = self.warp_point_with_status(itip.x, itip.y, w, h)
                dx, dy = point
                
                smooth_x = self.filters['x'].filter(dx)
                smooth_y = self.filters['y'].filter(dy)
                smooth_z = self.filters['z'].filter(itip.z)
                
                finger_states = self.classify_fingers(hand_landmarks)
                mouse_pose = self.is_mouse_pose(finger_states)
                
                tracked_data.append({
                    'raw': [dx, dy, itip.z],
                    'smooth': [smooth_x, smooth_y, smooth_z],
                    'finger_states': finger_states,
                    'mouse_pose': mouse_pose,
                    'handedness': handedness,
                    'handedness_score': handedness_score,
                    'in_bounds': in_bounds,
                    'landmarks': LandmarkCompat(hand_landmarks)
                })
        else:
            # We no longer have pinch filters to reset, but we keep the logic structure.
            pass
                
        return tracked_data
