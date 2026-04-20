import cv2
import mediapipe as mp
import numpy as np
from ..utils.filters import OneEuroFilter
from ..utils.config import ConfigManager

class TrackingEngine:
    def __init__(self, config_manager=None):
        self.config = config_manager or ConfigManager()
        self.config.load()
        
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        self.mp_draw = mp.solutions.drawing_utils
        
        # One-Euro Filters for X, Y, Z
        self.filters = {
            'x': OneEuroFilter(30, min_cutoff=0.1, beta=0.01),
            'y': OneEuroFilter(30, min_cutoff=0.1, beta=0.01),
            'z': OneEuroFilter(30, min_cutoff=0.5, beta=0.00)
        }

    def warp_point(self, x_norm, y_norm, img_w, img_h):
        px, py = x_norm * img_w, y_norm * img_h
        src_pt = np.array([[[px, py]]], dtype=np.float32)
        dst_pt = cv2.perspectiveTransform(src_pt, self.config.homography_matrix)
        return dst_pt[0][0]

    def calculate_pinch(self, landmarks):
        # 4 = Thumb Tip, 8 = Index Tip
        thumb = landmarks.landmark[4]
        index = landmarks.landmark[8]
        
        # 0 = Wrist, 5 = Index MCP (Palm scale proxy)
        wrist = landmarks.landmark[0]
        mcp = landmarks.landmark[5]
        
        # Euclidean distances
        pinch_dist = np.linalg.norm(np.array([thumb.x - index.x, thumb.y - index.y, thumb.z - index.z]))
        palm_dist = np.linalg.norm(np.array([wrist.x - mcp.x, wrist.y - mcp.y, wrist.z - mcp.z]))
        
        # Normalize distance (typical pinch is < 0.15 normalized)
        normalized_dist = pinch_dist / palm_dist
        return normalized_dist < 0.15 # Tunable threshold

    def process_frame(self, frame):
        h, w, _ = frame.shape
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb_frame)
        
        tracked_data = []
        
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                itip = hand_landmarks.landmark[8]
                desk_x, desk_y = self.warp_point(itip.x, itip.y, w, h)
                
                smooth_x = self.filters['x'].filter(desk_x)
                smooth_y = self.filters['y'].filter(desk_y)
                smooth_z = self.filters['z'].filter(itip.z)
                
                pinch_active = self.calculate_pinch(hand_landmarks)
                
                tracked_data.append({
                    'raw': [desk_x, desk_y, itip.z],
                    'smooth': [smooth_x, smooth_y, smooth_z],
                    'pinch_active': pinch_active,
                    'landmarks': hand_landmarks
                })
                
        return tracked_data
