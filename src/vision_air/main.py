import cv2
import numpy as np
import time
from multiprocessing import Process, Queue
from .core.tracking import TrackingEngine
from .core.keyboard_layout import KeyboardLayout
from .core.collision_detector import MultiFingerCollisionManager
from .utils.config import ConfigManager
from .input.controller import HIDController
from .ui.overlay import run_overlay_app

def draw_keyboard(view, layout):
    for char, bbox in layout.keys.items():
        x1, y1, x2, y2 = bbox
        px1, py1 = int(x1 * layout.width), int(y1 * layout.height)
        px2, py2 = int(x2 * layout.width), int(y2 * layout.height)
        cv2.rectangle(view, (px1, py1), (px2, py2), (100, 100, 100), 1)
        cv2.putText(view, char, (px1 + 10, py2 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)

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
    collision_managers = [MultiFingerCollisionManager(), MultiFingerCollisionManager()]

    # Initialize UI Overlay Process
    ui_queue = Queue()
    ui_process = Process(target=run_overlay_app, args=(config.desk_dims, ui_queue))
    ui_process.start()

    cap = cv2.VideoCapture(config.camera_index)
    desk_w, desk_h = config.desk_dims
    desk_view = np.zeros((desk_h, desk_w, 3), dtype=np.uint8)

    print("VISION-AIR Production Engine Online")
    print("Mode: AUTOMATIC (1 Hand = Mouse, 2 Hands = Keyboard)")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            results = engine.process_frame(frame)
            desk_view.fill(20)

            num_hands = len(results)
            mode = "MOUSE" if num_hands <= 1 else "KEYBOARD"
            
            # Prepare data for Overlay
            ui_data = {
                'mode': mode,
                'hand_data': results,
                'kb_layout': layout if mode == "KEYBOARD" else None
            }
            if not ui_queue.full():
                ui_queue.put(ui_data)

            if mode == "MOUSE" and num_hands == 1:
                hand = results[0]
                sx, sy, sz = hand['smooth']
                hid.move_to(sx, sy)
                hid.update_click_state(hand['pinch_active'])
                
                # Viz (OpenCV)
                color = (0, 0, 255) if hand['pinch_active'] else (0, 255, 0)
                cv2.circle(desk_view, (int(sx), int(sy)), 10, color, -1)

            elif mode == "KEYBOARD":
                draw_keyboard(desk_view, layout)
                for i, hand in enumerate(results[:2]):
                    hits = collision_managers[i].check_collisions(hand['landmarks'])
                    for fid, raw_x, raw_y in hits:
                        dx, dy = engine.warp_point(raw_x, raw_y, frame.shape[1], frame.shape[0])
                        key = layout.get_key_at(dx, dy)
                        if key:
                            hid.type_key(key)
                            cv2.circle(desk_view, (int(dx), int(dy)), 30, (255, 255, 255), 2)

            cv2.imshow("VISION-AIR - Camera Feed", frame)
            cv2.imshow("VISION-AIR - Desk View", desk_view)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()
        ui_process.terminate()

if __name__ == "__main__":
    main()
