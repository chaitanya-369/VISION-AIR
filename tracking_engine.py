import cv2
import mediapipe as mp
import numpy as np
import json
import time

class LowPassFilter:
    def __init__(self, alpha):
        self.alpha = alpha
        self.prev_value = None

    def filter(self, value):
        if self.prev_value is None:
            self.prev_value = value
            return value
        filtered = self.alpha * value + (1 - self.alpha) * self.prev_value
        self.prev_value = filtered
        return filtered

class OneEuroFilter:
    def __init__(self, freq, min_cutoff=1.0, beta=0.0, d_cutoff=1.0):
        self.freq = freq
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self.x_filter = LowPassFilter(self.alpha(min_cutoff))
        self.dx_filter = LowPassFilter(self.alpha(d_cutoff))
        self.last_time = None

    def alpha(self, cutoff):
        tau = 1.0 / (2 * np.pi * cutoff)
        te = 1.0 / self.freq
        return 1.0 / (1.0 + tau / te)

    def filter(self, x):
        curr_time = time.time()
        if self.last_time is None:
            self.last_time = curr_time
            return x
        
        dt = curr_time - self.last_time
        if dt <= 0:
            return x
        
        self.freq = 1.0 / dt
        self.last_time = curr_time

        # Filter velocity to compute dynamic cutoff
        prev_x = self.x_filter.prev_value
        dx = (x - prev_x) / dt if prev_x is not None else 0
        edx = self.dx_filter.filter(dx)
        
        cutoff = self.min_cutoff + self.beta * abs(edx)
        return self.x_filter.filter(x)

class TrackingEngine:
    def __init__(self, config_path="config.json"):
        self.load_config(config_path)
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        self.mp_draw = mp.solutions.drawing_utils
        
        # One-Euro Filters for X, Y, Z
        # Low min_cutoff = more smoothing at rest. Beta = how much it "opens up" during fast motion.
        self.filters = {
            'x': OneEuroFilter(30, min_cutoff=0.1, beta=0.01),
            'y': OneEuroFilter(30, min_cutoff=0.1, beta=0.01),
            'z': OneEuroFilter(30, min_cutoff=0.5, beta=0.00) # Keep Z very smooth
        }

    def load_config(self, path):
        if not os.path.exists(path):
            raise FileNotFoundError(f"Config not found at {path}. Run calibration.py first.")
        with open(path, "r") as f:
            config = json.load(f)
        self.camera_index = config["camera_index"]
        self.H = np.array(config["homography_matrix"])
        self.desk_dims = config["desk_dims"]

    def warp_point(self, x_norm, y_norm, img_w, img_h):
        # Normalization to Pixel coords
        px, py = x_norm * img_w, y_norm * img_h
        
        # Apply Homography
        src_pt = np.array([[[px, py]]], dtype=np.float32)
        dst_pt = cv2.perspectiveTransform(src_pt, self.H)
        
        # Returns (x, y) in Desk Pixel Coords (e.g. 0-1280, 0-720)
        return dst_pt[0][0]

    def process_frame(self, frame):
        h, w, _ = frame.shape
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb_frame)
        
        tracked_data = []
        
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                # Focus on Index Finger Tip (Landmark 8)
                itip = hand_landmarks.landmark[8]
                
                # Warp to Desk Space
                desk_x, desk_y = self.warp_point(itip.x, itip.y, w, h)
                
                # Smooth
                smooth_x = self.filters['x'].filter(desk_x)
                smooth_y = self.filters['y'].filter(desk_y)
                smooth_z = self.filters['z'].filter(itip.z) # MediaPipe Raw Z
                
                tracked_data.append({
                    'raw': [desk_x, desk_y, itip.z],
                    'smooth': [smooth_x, smooth_y, smooth_z],
                    'landmarks': hand_landmarks
                })
                
        return tracked_data

import os # Needed check inside load_config
