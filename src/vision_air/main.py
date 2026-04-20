import cv2
import numpy as np
import time
import sys
from multiprocessing import Process, Queue

# Standard project imports
from .core.tracking import TrackingEngine
from .core.keyboard_layout import KeyboardLayout
from .core.collision_detector import MultiFingerCollisionManager
from .utils.config import ConfigManager
from .input.controller import HIDController
from .ui.overlay import run_overlay_app

def main():
    print("[INFO] Starting VISION-AIR System...")
    config = ConfigManager()
    
    if not hasattr(config, 'matrix'):
        print("[ERROR] Calibration not found! Please run Option 2 first.")
        input("Press Enter to continue...")
        return

    try:
        engine = TrackingEngine(config_manager=config)
    except Exception as e:
        print(f"[ERROR] Failed to initialize engine: {e}")
        input("Press Enter to exit...")
        return

    hid = HIDController(config.desk_dims)
    layout = KeyboardLayout(config.desk_dims)
    collision_managers = [MultiFingerCollisionManager(), MultiFingerCollisionManager()]
    
    cap = cv2.VideoCapture(config.camera_index)
    
    # UI Setup
    ui_queue = Queue(maxsize=1)
    ui_process = Process(target=run_overlay_app, args=(config.desk_dims, ui_queue))
    ui_process.start()

    desk_view = np.zeros((config.desk_dims[1], config.desk_dims[0], 3), dtype=np.uint8)

    print("[INFO] Engine Ready. Press 'q' in the window to exit.")
    
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
                # Warp the index tip
                raw_x, raw_y = hand['smooth'][0], hand['smooth'][1]
                dx, dy = engine.warp_point(raw_x, raw_y, frame.shape[1], frame.shape[0])
                
                hid.move_to(dx, dy)
                hid.update_click_state(hand['pinch_active'])
                
                # Visuals
                color = (0, 0, 255) if hand['pinch_active'] else (0, 255, 0)
                cv2.circle(desk_view, (int(dx), int(dy)), 10, color, -1)

            elif mode == "KEYBOARD":
                # Draw grid in debug view
                for key_name, rect in layout.keys.items():
                    cv2.rectangle(desk_view, (rect[0], rect[1]), (rect[2], rect[3]), (100, 100, 100), 1)
                
                for i, hand in enumerate(results[:2]):
                    # Check collisions for all fingertips
                    for tip_idx in [4, 8, 12, 16, 20]:
                        lm = hand['landmarks'][tip_idx]
                        dx, dy = engine.warp_point(lm.x, lm.y, frame.shape[1], frame.shape[0])
                        key = layout.get_key_at(dx, dy)
                        if key:
                            # Note: Simplified collision for now, just checking if in rect
                            # In production we'd use the CollisionManager's depth-velocity logic
                            cv2.circle(desk_view, (int(dx), int(dy)), 20, (255, 255, 255), 2)

            cv2.imshow("VISION-AIR - Camera Feed", frame)
            cv2.imshow("VISION-AIR - Desk View", desk_view)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    except Exception as e:
        print(f"[FATAL ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        cap.release()
        cv2.destroyAllWindows()
        ui_process.terminate()
        print("[INFO] Shutdown complete. Press Enter.")
        input()

if __name__ == "__main__":
    main()
