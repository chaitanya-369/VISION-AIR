import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import os

class TrackingEngine:
    """
    Tracking Engine using the modern MediaPipe Tasks API.
    Provides better performance and stability on Python 3.12/3.13.
    """
    def __init__(self, config_manager):
        self.config = config_manager
        
        # Load the task model
        # We'll use the official hand_landmarker.task file
        # If it doesn't exist, we'll try to use a fallback or provide instructions
        base_options = python.BaseOptions(model_asset_path='hand_landmarker.task')
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=2,
            min_hand_detection_confidence=0.5,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        try:
            self.detector = vision.HandLandmarker.create_from_options(options)
        except Exception as e:
            print(f"[ERROR] Could not load MediaPipe Task: {e}")
            print("[TIP] Downloading modern hand landmarker model...")
            self._download_model()
            self.detector = vision.HandLandmarker.create_from_options(options)

    def _download_model(self):
        import urllib.request
        url = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
        urllib.request.urlretrieve(url, "hand_landmarker.task")
        print("[SUCCESS] Hand Landmarker model downloaded.")

    def process_frame(self, frame):
        # Convert frame to MediaPipe Image
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
        
        # Detect
        detection_result = self.detector.detect(mp_image)
        
        results = []
        if detection_result.hand_landmarks:
            for i, landmarks in enumerate(detection_result.hand_landmarks):
                # Format to match our existing logic
                # Landsmarks in Tasks API are a list of landmarks
                results.append({
                    'landmarks': landmarks,
                    'world_landmarks': detection_result.hand_world_landmarks[i],
                    'handedness': detection_result.handedness[i][0].category_name,
                    # Calculate pinch based on index and thumb
                    'pinch_active': self._is_pinching(landmarks),
                    # Smooth coordinates (unwarped for now, warped in main)
                    'smooth': self._get_smooth_tip(landmarks)
                })
        return results

    def _is_pinching(self, landmarks):
        # Index tip (8) and Thumb tip (4)
        it = landmarks[8]
        tt = landmarks[4]
        dist = np.sqrt((it.x - tt.x)**2 + (it.y - tt.y)**2)
        return dist < 0.05 # Threshold

    def _get_smooth_tip(self, landmarks):
        # For now just return raw index tip
        it = landmarks[8]
        return (it.x, it.y, it.z)

    def warp_point(self, x, y, frame_w, frame_h):
        # Use existing homography logic
        src_pt = np.array([[[x * frame_w, y * frame_h]]], dtype=np.float32)
        warped = cv2.perspectiveTransform(src_pt, self.config.matrix)
        if warped is not None:
            return warped[0][0][0], warped[0][0][1]
        return 0, 0
