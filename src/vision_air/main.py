import cv2
import numpy as np
import time
from .core.tracking import TrackingEngine
from .core.keyboard_layout import KeyboardLayout
from .core.collision_detector import MultiFingerCollisionManager
from .utils.config import ConfigManager
from .input.controller import HIDController

def draw_keyboard(view, layout):
    for char, bbox in layout.keys.items():
        x1, y1, x2, y2 = bbox
        px1, py1 = int(x1 * layout.width), int(y1 * layout.height)
        px2, py2 = int(x2 * layout.width), int(y2 * layout.height)
        
        cv2.rectangle(view, (px1, py1), (px2, py2), (100, 100, 100), 1)
        cv2.putText(view, char, (px1 + 10, py2 - 10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)

def main():
    config = ConfigManager()
    try:
        engine = TrackingEngine(config_manager=config)
    except Exception as e:
        print(f"Initialization failed: {e}")
        print("Please run calibration first.")
        return

    hid = HIDController(config.desk_dims)
    layout = KeyboardLayout(config.desk_dims)
    
    # Track collisions for multiple fingers
    collision_managers = [MultiFingerCollisionManager(), MultiFingerCollisionManager()]

    cap = cv2.VideoCapture(config.camera_index)
    desk_w, desk_h = config.desk_dims
    desk_view = np.zeros((desk_h, desk_w, 3), dtype=np.uint8)

    print("VISION-AIR Production Engine Online")
    print("Mode: AUTOMATIC (1 Hand = Mouse, 2 Hands = Keyboard)")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        results = engine.process_frame(frame)
        desk_view.fill(20)

        num_hands = len(results)
        
        if num_hands == 1:
            # --- MOUSE MODE ---
            hand = results[0]
            engine.mp_draw.draw_landmarks(frame, hand['landmarks'], engine.mp_hands.HAND_CONNECTIONS)
            sx, sy, sz = hand['smooth']
            hid.move_to(sx, sy)
            hid.update_click_state(hand['pinch_active'])
            
            # Viz
            color = (0, 0, 255) if hand['pinch_active'] else (0, 255, 0)
            cv2.circle(desk_view, (int(sx), int(sy)), 10, color, -1)
            cv2.putText(desk_view, "MOUSE MODE", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        elif num_hands >= 2:
            # --- KEYBOARD MODE ---
            draw_keyboard(desk_view, layout)
            cv2.putText(desk_view, "KEYBOARD MODE", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            
            for i, hand in enumerate(results[:2]): # Max 2 hands
                engine.mp_draw.draw_landmarks(frame, hand['landmarks'], engine.mp_hands.HAND_CONNECTIONS)
                
                # Check collisions for fingertips
                hits = collision_managers[i].check_collisions(hand['landmarks'])
                for fid, raw_x, raw_y in hits:
                    # Map raw normalized coords to desk coords for key detection
                    # (Note: we use raw landmarks for collisions because they have higher Z-velocity fidelity)
                    dx, dy = engine.warp_point(raw_x, raw_y, frame.shape[1], frame.shape[0])
                    key = layout.get_key_at(dx, dy)
                    if key:
                        hid.type_key(key)
                        # Visual hit feedback
                        cv2.circle(desk_view, (int(dx), int(dy)), 30, (255, 255, 255), 2)

        cv2.imshow("VISION-AIR - Camera Feed", frame)
        cv2.imshow("VISION-AIR - Desk View", desk_view)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
