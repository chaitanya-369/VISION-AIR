import cv2
import numpy as np
import json
import os

class DeskCalibrator:
    def __init__(self, camera_index=0):
        self.camera_index = camera_index
        self.points = []
        self.window_name = "VISION-AIR Calibration - Click 4 Corners of your Desk"
        
    def mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            if len(self.points) < 4:
                self.points.append([x, y])
                print(f"Point {len(self.points)} recorded: {x, y}")

    def run(self):
        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            print("Error: Could not open camera.")
            return

        cv2.namedWindow(self.window_name)
        cv2.setMouseCallback(self.window_name, self.mouse_callback)

        print("\nINSTRUCTIONS:")
        print("1. Click the TOP-LEFT corner of your desk.")
        print("2. Click the TOP-RIGHT corner of your desk.")
        print("3. Click the BOTTOM-RIGHT corner of your desk.")
        print("4. Click the BOTTOM-LEFT corner of your desk.")
        print("Press 'r' to reset points, 'q' to quit, 's' to save (after 4 points).")

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Draw recorded points
            for p in self.points:
                cv2.circle(frame, tuple(p), 5, (0, 255, 0), -1)
            
            # Connect points with lines if all 4 are selected
            if len(self.points) == 4:
                pts = np.array(self.points, np.int32)
                cv2.polylines(frame, [pts], True, (255, 0, 0), 2)
                cv2.putText(frame, "Press 's' to save and preview", (10, 30), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            cv2.imshow(self.window_name, frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'):
                self.points = []
            elif key == ord('s') and len(self.points) == 4:
                self.save_and_preview(frame)
                break

        cap.release()
        cv2.destroyAllWindows()

    def save_and_preview(self, frame):
        # Target dimensions (e.g., 1280x720)
        width, height = 1280, 720
        src_pts = np.float32(self.points)
        dst_pts = np.float32([[0, 0], [width, 0], [width, height], [0, height]])
        
        matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
        
        # Preview warp
        warped = cv2.warpPerspective(frame, matrix, (width, height))
        cv2.imshow("Preview - Desk View (Warped)", warped)
        print("Previewing warped desk view. Press any key to confirm and save.")
        cv2.waitKey(0)
        
        # Save config
        config = {
            "camera_index": self.camera_index,
            "homography_matrix": matrix.tolist(),
            "desk_dims": [width, height]
        }
        
        with open("config.json", "w") as f:
            json.dump(config, f, indent=4)
        
        print("Configuration saved to config.json")

if __name__ == "__main__":
    calibrator = DeskCalibrator()
    calibrator.run()
