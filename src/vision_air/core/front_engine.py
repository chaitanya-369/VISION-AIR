import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import numpy as np
import os
import time

class FrontEngine:
    """
    Vertical Contact Engine (Front-View).
    Processes feed from the monitor stand to detect fingertip-to-desk collision.
    """
    def __init__(self, desk_y_floor=0.8, floor_corners=None):
        self.desk_y_floor = desk_y_floor
        self.floor_corners = floor_corners or [[0.0, 0.8], [1.0, 0.8], [1.0, 0.9], [0.0, 0.9]]
        
        # Path to the .task model
        model_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "assets", "models", "hand_landmarker.task")
        if not os.path.exists(model_path):
            model_path = os.path.join(os.getcwd(), "assets", "models", "hand_landmarker.task")

        base_options = python.BaseOptions(
            model_asset_path=model_path,
            delegate=python.BaseOptions.Delegate.CPU 
        )
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=2,
            min_hand_detection_confidence=0.6,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5,
            running_mode=vision.RunningMode.VIDEO
        )
        self.landmarker = vision.HandLandmarker.create_from_options(options)
        self.last_timestamp_ms = 0
        self.start_time = time.monotonic()

    def _next_timestamp(self):
        ts = int((time.monotonic() - self.start_time) * 1000)
        if ts <= self.last_timestamp_ms:
            ts = self.last_timestamp_ms + 1
        self.last_timestamp_ms = ts
        return ts

    def get_expected_y(self, u, v):
        """
        Calculates the expected Y coordinate (floor height) for a given desk position (u, v).
        u, v are normalized [0, 1] coordinates from the top view.
        Uses Bilinear Interpolation across 4 points.
        """
        # Corners: TL, TR, BR, BL
        y1 = self.floor_corners[0][1]
        y2 = self.floor_corners[1][1]
        y3 = self.floor_corners[2][1]
        y4 = self.floor_corners[3][1]
        
        # Bilinear interpolation formula for the Y height
        expected_y = (1-u)*(1-v)*y1 + u*(1-v)*y2 + u*v*y3 + (1-u)*v*y4
        return expected_y

    def process_frame(self, frame, hand_desk_pos=None):
        """
        Analyzes the front-view frame to find contact events.
        If hand_desk_pos (u, v) is provided, it uses the dynamic bilinear floor.
        """
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        
        results = self.landmarker.detect_for_video(mp_image, self._next_timestamp())
        
        contact_data = []
        if results.hand_landmarks:
            for hand_landmarks in results.hand_landmarks:
                # Track all 5 fingertips: 4, 8, 12, 16, 20
                fingers = {}
                for idx in [4, 8, 12, 16, 20]:
                    tip = hand_landmarks[idx]
                    
                    # Determine the floor height for this specific finger
                    # If we don't have the desk mapping, fallback to static line
                    floor_y = self.desk_y_floor
                    if hand_desk_pos:
                        u, v = hand_desk_pos
                        floor_y = self.get_expected_y(u, v)

                    # In front view, tip.y is the vertical axis.
                    # As finger goes DOWN to desk, tip.y INCREASES (0 top, 1 bottom)
                    is_touching = tip.y >= floor_y
                    fingers[idx] = {
                        "x": tip.x,         # Used for cross-camera association
                        "y": tip.y,         # Height
                        "floor_y": floor_y, # Dynamic reference line
                        "is_touching": is_touching,
                    }
                contact_data.append(fingers)
                
        return contact_data
