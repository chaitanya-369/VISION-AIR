import cv2
import numpy as np
from ..utils.config import ConfigManager

class DeskCalibrator:
    def __init__(self, camera_index=0, config_manager=None):
        self.camera_index = camera_index
        self.config = config_manager or ConfigManager()
        self.points = []
        self.window_name = "VISION-AIR Calibration - Click 4 Corners of your Desk"
        self.axis_correction = {"swap_xy": False, "invert_x": False, "invert_y": False}
        
    def mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            if len(self.points) < 4:
                self.points.append([x, y])
                print(f"Point {len(self.points)} recorded: {x, y}")

    def run(self):
        print("\nCAMERA SETUP:")
        print("Press 'c' to cycle through available camera indices.")
        print("Press 'i' to enter an IP Camera URL (e.g., http://192.168.1.5:4747/video)")
        print("After selecting 4 corners, press 's' to preview. In preview: 't'=swap axes, 'x'/'y'=flip, 's'=save.")
        
        cap = cv2.VideoCapture(self.camera_index)
        
        cv2.namedWindow(self.window_name)
        cv2.setMouseCallback(self.window_name, self.mouse_callback)

        while True:
            ret, frame = cap.read()
            if not ret:
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(frame, f"FAILED TO OPEN CAMERA {self.camera_index}", (50, 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                cv2.imshow(self.window_name, frame)
            else:
                # Draw recorded points
                for p in self.points:
                    cv2.circle(frame, tuple(p), 5, (0, 255, 0), -1)
                
                if len(self.points) == 4:
                    pts = np.array(self.points, np.int32)
                    cv2.polylines(frame, [pts], True, (255, 0, 0), 2)
                    cv2.putText(frame, "Press 's' to preview/save controls", (10, 30),
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

    def order_points(self):
        pts = np.array(self.points, dtype=np.float32)
        ordered = np.zeros((4, 2), dtype=np.float32)

        sums = pts.sum(axis=1)
        diffs = np.diff(pts, axis=1).reshape(-1)
        ordered[0] = pts[np.argmin(sums)]   # top-left
        ordered[1] = pts[np.argmin(diffs)]  # top-right
        ordered[2] = pts[np.argmax(sums)]   # bottom-right
        ordered[3] = pts[np.argmax(diffs)]  # bottom-left
        return ordered

    def apply_axis_preview(self, image):
        preview = image
        height, width = image.shape[:2]

        if self.axis_correction["swap_xy"]:
            preview = cv2.transpose(preview)
            preview = cv2.resize(preview, (width, height), interpolation=cv2.INTER_LINEAR)
        if self.axis_correction["invert_x"]:
            preview = cv2.flip(preview, 1)
        if self.axis_correction["invert_y"]:
            preview = cv2.flip(preview, 0)

        return preview

    def axis_status(self):
        return (
            f"swap_xy={self.axis_correction['swap_xy']}  "
            f"invert_x={self.axis_correction['invert_x']}  "
            f"invert_y={self.axis_correction['invert_y']}"
        )

    def draw_preview_help(self, preview):
        cv2.rectangle(preview, (0, 0), (preview.shape[1], 96), (0, 0, 0), -1)
        cv2.putText(preview, "Preview controls: T swap X/Y | X flip horizontal | Y flip vertical | R reset | S/Enter save | Q cancel",
                    (16, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
        cv2.putText(preview, self.axis_status(),
                    (16, 68), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)

    def save_and_preview(self, frame):
        width, height = 1280, 720
        src_pts = self.order_points()
        dst_pts = np.float32([[0, 0], [width, 0], [width, height], [0, height]])
        
        matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)

        print("Previewing warped desk view.")
        print("Use T if horizontal movement maps to vertical. Use X/Y if an axis is mirrored. Press S or Enter to save.")
        while True:
            warped = cv2.warpPerspective(frame, matrix, (width, height))
            preview = self.apply_axis_preview(warped)
            self.draw_preview_help(preview)
            cv2.imshow("Preview - Desk View (Warped)", preview)

            key = cv2.waitKey(0) & 0xFF
            if key in (ord('s'), 13, 10):
                break
            if key in (ord('q'), 27):
                print("Calibration cancelled. Existing config was not changed.")
                cv2.destroyWindow("Preview - Desk View (Warped)")
                return
            if key in (ord('t'), ord('T')):
                self.axis_correction["swap_xy"] = not self.axis_correction["swap_xy"]
                print(f"[CALIBRATION] {self.axis_status()}")
            elif key in (ord('x'), ord('X')):
                self.axis_correction["invert_x"] = not self.axis_correction["invert_x"]
                print(f"[CALIBRATION] {self.axis_status()}")
            elif key in (ord('y'), ord('Y')):
                self.axis_correction["invert_y"] = not self.axis_correction["invert_y"]
                print(f"[CALIBRATION] {self.axis_status()}")
            elif key in (ord('r'), ord('R')):
                self.axis_correction = {"swap_xy": False, "invert_x": False, "invert_y": False}
                print(f"[CALIBRATION] {self.axis_status()}")
        
        config_data = {
            "camera_index": self.camera_index,
            "homography_matrix": matrix.tolist(),
            "desk_dims": [width, height],
            "axis_correction": self.axis_correction,
        }
        
        self.config.save(config_data)
        cv2.destroyWindow("Preview - Desk View (Warped)")
        print("Configuration saved via ConfigManager.")

def main():
    calibrator = DeskCalibrator()
    calibrator.run()

if __name__ == "__main__":
    main()
