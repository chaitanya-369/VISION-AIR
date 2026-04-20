import cv2
import numpy as np
from .core.tracking import TrackingEngine
from .utils.config import ConfigManager

def main():
    config = ConfigManager()
    try:
        engine = TrackingEngine(config_manager=config)
    except Exception as e:
        print(f"Initialization failed: {e}")
        print("Please run calibration first.")
        # We could trigger calibration here automatically in the future
        return

    cap = cv2.VideoCapture(config.camera_index)
    desk_w, desk_h = config.desk_dims
    desk_view = np.zeros((desk_h, desk_w, 3), dtype=np.uint8)

    print("VISION-AIR Production Engine Started")
    print("Press 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        results = engine.process_frame(frame)
        desk_view.fill(20)

        for hand in results:
            engine.mp_draw.draw_landmarks(frame, hand['landmarks'], engine.mp_hands.HAND_CONNECTIONS)
            
            sx, sy, sz = hand['smooth']
            sx = int(np.clip(sx, 0, desk_w))
            sy = int(np.clip(sy, 0, desk_h))
            
            radius = int(max(5, 20 - (sz * 100)))
            cv2.circle(desk_view, (sx, sy), radius, (0, 255, 0), -1)

        cv2.imshow("Camera View", frame)
        cv2.imshow("Desk View", desk_view)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
