import cv2
import numpy as np
from ..utils.config import ConfigManager

class DeskCalibrator:
    def __init__(self, camera_index=0, config_manager=None):
        self.camera_index = camera_index
        self.config = config_manager or ConfigManager()
        self.points = []
        self.window_name = "VISION-AIR Calibration - Click 4 Corners of your Desk"
        
    def mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            if len(self.points) < 4:
                self.points.append([x, y])
                print(f"Point {len(self.points)} recorded: {x, y}")

    def run(self):
        print("\nCAMERA SETUP:")
        print("Press 'c' to cycle through available camera indices.")
        print("Press 'i' to enter an IP Camera URL (e.g., http://192.168.1.5:4747/video)")
        
        cap = cv2.VideoCapture(self.camera_index)
        
        cv2.namedWindow(self.window_name)
        cv2.setMouseCallback(self.window_name, self.mouse_callback)

        while True:
            ret, frame = cap.read()
            if not ret:
                cv2.putText(frame, f"FAILED TO OPEN CAMERA {self.camera_index}", (50, 50), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                cv2.imshow(self.window_name, np.zeros((480, 640, 3), dtype=np.uint8))
            else:
                # Draw recorded points
                for p in self.points:
                    cv2.circle(frame, tuple(p), 5, (0, 255, 0), -1)
                
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
            elif key == ord('c'):
                # Cycle camera index
                self.camera_index = (self.camera_index + 1) % 5
                cap.release()
                cap = cv2.VideoCapture(self.camera_index)
                print(f"Switched to Camera Index: {self.camera_index}")
            elif key == ord('i'):
                # IP Camera URL Input
                url = input("\nEnter IP Camera URL: ")
                if url:
                    self.camera_index = url
                    cap.release()
                    cap = cv2.VideoCapture(self.camera_index)
            elif key == ord('s') and len(self.points) == 4:
                self.save_and_preview(frame)
                break

        cap.release()
        cv2.destroyAllWindows()

    def save_and_preview(self, frame):
        width, height = 1280, 720
        src_pts = np.float32(self.points)
        dst_pts = np.float32([[0, 0], [width, 0], [width, height], [0, height]])
        
        matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
        
        warped = cv2.warpPerspective(frame, matrix, (width, height))
        cv2.imshow("Preview - Desk View (Warped)", warped)
        print("Previewing warped desk view. Press any key to confirm and save.")
        cv2.waitKey(0)
        
        config_data = {
            "camera_index": self.camera_index,
            "homography_matrix": matrix.tolist(),
            "desk_dims": [width, height]
        }
        
        self.config.save(config_data)
        print("Configuration saved via ConfigManager.")

if __name__ == "__main__":
    calibrator = DeskCalibrator()
    calibrator.run()
