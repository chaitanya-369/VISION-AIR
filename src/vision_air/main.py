import cv2
import numpy as np
from .core.tracking import TrackingEngine
from .utils.config import ConfigManager
from .input.controller import HIDController

def main():
    config = ConfigManager()
    try:
        engine = TrackingEngine(config_manager=config)
    except Exception as e:
        print(f"Initialization failed: {e}")
        print("Please run calibration first.")
        return

    # Initialize HID Controller
    hid = HIDController(config.desk_dims)

    cap = cv2.VideoCapture(config.camera_index)
    desk_w, desk_h = config.desk_dims
    desk_view = np.zeros((desk_h, desk_w, 3), dtype=np.uint8)

    print("VISION-AIR Production Engine Started - MOUSE MODE ACTIVE")
    print("Press 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        results = engine.process_frame(frame)
        desk_view.fill(20)

        # We assume single-hand control for now
        if results:
            hand = results[0] # Primary hand
            engine.mp_draw.draw_landmarks(frame, hand['landmarks'], engine.mp_hands.HAND_CONNECTIONS)
            
            sx, sy, sz = hand['smooth']
            
            # Map and move mouse
            hid.move_to(sx, sy)
            
            # Handle clicking
            hid.update_click_state(hand['pinch_active'])
            
            # Visualization
            sx_clamped = int(np.clip(sx, 0, desk_w))
            sy_clamped = int(np.clip(sy, 0, desk_h))
            
            color = (0, 0, 255) if hand['pinch_active'] else (0, 255, 0)
            radius = int(max(5, 20 - (sz * 100)))
            cv2.circle(desk_view, (sx_clamped, sy_clamped), radius, color, -1)
            if hand['pinch_active']:
                cv2.putText(desk_view, "CLICK", (sx_clamped + 20, sy_clamped), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        cv2.imshow("Camera View", frame)
        cv2.imshow("Desk View", desk_view)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
