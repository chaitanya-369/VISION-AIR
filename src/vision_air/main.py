import cv2
import numpy as np
import time
import sys
import os
from multiprocessing import Process, Queue

# Standard project imports
from .core.tracking import TrackingEngine
from .core.front_engine import FrontEngine
from .core.keyboard_layout import KeyboardLayout
from .core.collision_detector import RightHandTapManager
from .utils.config import ConfigManager
from .input.controller import HIDController
from .ui.overlay import run_overlay_app

HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (0, 9), (9, 10), (10, 11), (11, 12),
    (0, 13), (13, 14), (14, 15), (15, 16),
    (0, 17), (17, 18), (18, 19), (19, 20),
    (5, 9), (9, 13), (13, 17), (17, 0),
]
FINGERTIP_LABELS = {4: "T", 8: "I", 12: "M", 16: "R", 20: "P"}

def axis_status(config):
    correction = config.axis_correction
    return (
        f"swap={correction.get('swap_xy', False)} "
        f"flip_x={correction.get('invert_x', False)} "
        f"flip_y={correction.get('invert_y', False)}"
    )

def toggle_axis(config, key):
    correction = dict(config.axis_correction)
    if key in (ord('t'), ord('T')):
        correction["swap_xy"] = not correction.get("swap_xy", False)
    elif key in (ord('x'), ord('X')):
        correction["invert_x"] = not correction.get("invert_x", False)
    elif key in (ord('y'), ord('Y')):
        correction["invert_y"] = not correction.get("invert_y", False)
    elif key in (ord('r'), ord('R')):
        correction = {"swap_xy": False, "invert_x": False, "invert_y": False}
    else:
        return

    config.config["axis_correction"] = correction
    config.save(config.config)
    print(f"[AXIS] Saved {axis_status(config)}")

def draw_debug_text(image, mode, config, hid, hand=None, tap_debug=None, include_panel=True):
    lines = [
        f"Mode: {mode} | HID: {'ON' if hid.enabled else 'OFF'} | {axis_status(config)}",
        "Keys: Q quit | H HID on/off | V preview | C camera raw/corrected | T swap X/Y | X flip horizontal | Y flip vertical | R reset axes",
    ]
    if hand:
        dx, dy, _ = hand["smooth"]
        hand_label = hand.get("handedness", "?")
        hand_conf = hand.get("handedness_score", 0)
        lines.append(
            f"Hand: {hand_label} {hand_conf:.2f} | mouse_pose={hand.get('mouse_pose')} | "
            f"Desk: {int(dx)}, {int(dy)} | in_bounds={hand.get('in_bounds')} "
        )
    if tap_debug:
        lines.append(tap_debug)
    
    lines.append(f"Floor Line: {config.desk_y_floor:.3f} (Adjust with [ and ])")

    if include_panel:
        panel_h = 18 + len(lines) * 26
        cv2.rectangle(image, (0, 0), (image.shape[1], panel_h), (0, 0, 0), -1)

    for i, line in enumerate(lines):
        y = 28 + i * 26
        cv2.putText(image, line, (16, y), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (230, 230, 230), 2)

def to_int_point(point):
    x, y = point
    if not np.isfinite(x) or not np.isfinite(y):
        return None
    return int(round(x)), int(round(y))

def landmark_camera_point(landmark, frame_shape):
    h, w = frame_shape[:2]
    return to_int_point((landmark.x * w, landmark.y * h))

def apply_axis_transform_to_image(image, correction):
    transformed = image
    h, w = image.shape[:2]

    if correction.get("swap_xy", False):
        transformed = cv2.transpose(transformed)
        transformed = cv2.resize(transformed, (w, h), interpolation=cv2.INTER_LINEAR)
    if correction.get("invert_x", False):
        transformed = cv2.flip(transformed, 1)
    if correction.get("invert_y", False):
        transformed = cv2.flip(transformed, 0)

    return transformed

def apply_axis_transform_to_point(point, frame_shape, correction):
    h, w = frame_shape[:2]
    x, y = point

    if correction.get("swap_xy", False):
        x, y = (y / h) * w, (x / w) * h
    if correction.get("invert_x", False):
        x = w - x
    if correction.get("invert_y", False):
        y = h - y

    return to_int_point((x, y))

def draw_hand_landmarks_on_camera(frame, hand, correction=None):
    landmarks = hand["landmarks"]
    points = []
    for lm in landmarks:
        point = landmark_camera_point(lm, frame.shape)
        if point and correction:
            point = apply_axis_transform_to_point(point, frame.shape, correction)
        points.append(point)

    line_color = (70, 220, 255)
    dot_color = (0, 210, 255) if hand.get("mouse_pose") else (130, 130, 130)
    tip_color = (0, 255, 0)

    for start, end in HAND_CONNECTIONS:
        if points[start] and points[end]:
            cv2.line(frame, points[start], points[end], line_color, 2, cv2.LINE_AA)

    for idx, point in enumerate(points):
        if not point:
            continue
        radius = 5 if idx in FINGERTIP_LABELS else 3
        color = tip_color if idx in FINGERTIP_LABELS else dot_color
        cv2.circle(frame, point, radius, color, -1, cv2.LINE_AA)
        if idx in FINGERTIP_LABELS:
            cv2.putText(frame, FINGERTIP_LABELS[idx], (point[0] + 6, point[1] - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)

    wrist = points[0] or (16, 64)
    cv2.putText(frame, f"{hand.get('handedness', '?')} pose={hand.get('mouse_pose')}",
                (wrist[0] + 12, wrist[1] + 24), cv2.FONT_HERSHEY_SIMPLEX,
                0.55, (255, 255, 255), 2, cv2.LINE_AA)

def draw_desk_guides(desk_view, desk_dims):
    desk_w, desk_h = desk_dims
    grid_color = (35, 35, 35)
    axis_color = (90, 90, 90)

    for x in range(0, desk_w + 1, desk_w // 8):
        cv2.line(desk_view, (x, 0), (x, desk_h), grid_color, 1)
    for y in range(0, desk_h + 1, desk_h // 6):
        cv2.line(desk_view, (0, y), (desk_w, y), grid_color, 1)

    cv2.rectangle(desk_view, (0, 0), (desk_w - 1, desk_h - 1), (80, 80, 80), 2)
    cv2.arrowedLine(desk_view, (40, desk_h - 40), (180, desk_h - 40), axis_color, 2, tipLength=0.18)
    cv2.arrowedLine(desk_view, (40, desk_h - 40), (40, desk_h - 180), axis_color, 2, tipLength=0.18)
    cv2.putText(desk_view, "+X", (190, desk_h - 32), cv2.FONT_HERSHEY_SIMPLEX, 0.6, axis_color, 2)
    cv2.putText(desk_view, "+Y", (18, desk_h - 190), cv2.FONT_HERSHEY_SIMPLEX, 0.6, axis_color, 2)

def draw_hand_landmarks_on_desk(desk_view, hand, engine, frame_shape):
    h, w = frame_shape[:2]
    landmarks = hand["landmarks"]
    points = []
    for lm in landmarks:
        point = engine.warp_point(lm.x, lm.y, w, h)
        points.append(to_int_point(point))

    line_color = (0, 190, 230)
    dot_color = (0, 210, 255) if hand.get("mouse_pose") else (130, 130, 130)
    tip_color = (0, 255, 0)

    for start, end in HAND_CONNECTIONS:
        if points[start] and points[end]:
            cv2.line(desk_view, points[start], points[end], line_color, 2, cv2.LINE_AA)

    for idx, point in enumerate(points):
        if not point:
            continue
        radius = 7 if idx in FINGERTIP_LABELS else 4
        color = tip_color if idx in FINGERTIP_LABELS else dot_color
        cv2.circle(desk_view, point, radius, color, -1, cv2.LINE_AA)
        if idx in FINGERTIP_LABELS:
            cv2.putText(desk_view, FINGERTIP_LABELS[idx], (point[0] + 9, point[1] - 9),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2, cv2.LINE_AA)

    wrist = points[0] or (16, 120)
    cv2.putText(desk_view, f"{hand.get('handedness', '?')} pose={hand.get('mouse_pose')}",
                (wrist[0] + 12, wrist[1] + 24), cv2.FONT_HERSHEY_SIMPLEX,
                0.55, (255, 255, 255), 2, cv2.LINE_AA)



def get_right_hand(results):
    right_hands = [hand for hand in results if hand.get("handedness") == "Right"]
    if not right_hands:
        return None
    return max(right_hands, key=lambda hand: hand.get("handedness_score", 0))

def main():
    print("[INFO] Starting VISION-AIR System (Stability Mode)...")
    config = ConfigManager()
    
    try:
        config.load()
        _ = config.homography_matrix
    except (FileNotFoundError, KeyError, ValueError) as e:
        print("[ERROR] Calibration not found! Please run Option 2 first.")
        print(f"[DETAIL] {e}")
        input("Press Enter to continue...")
        return

    # Check for model asset
    model_path = os.path.join("assets", "models", "hand_landmarker.task")
    if not os.path.exists(model_path):
        print("[INFO] Model not found. Downloading the AI 'Brain' (~5MB)...")
        import urllib.request
        url = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
        try:
            os.makedirs(os.path.dirname(model_path), exist_ok=True)
            urllib.request.urlretrieve(url, model_path)
            print("[SUCCESS] Download complete.")
        except Exception as e:
            print(f"[FATAL] Connection error: {e}")
            input("Press Enter to exit...")
            return

    try:
        engine = TrackingEngine(config_manager=config)
    except Exception as e:
        print(f"[ERROR] Engine failed to start: {e}")
        input("Press Enter to exit...")
        return

    hid = HIDController(config.desk_dims)
    layout = KeyboardLayout(config.desk_dims)
    tap_manager = RightHandTapManager()
    
    # Dual Camera Setup
    cap_top = cv2.VideoCapture(config.camera_index)
    cap_front = cv2.VideoCapture(config.camera_front_index)
    
    # Front-View Collision Engine
    engine_front = FrontEngine(
        desk_y_floor=config.desk_y_floor,
        floor_corners=config.front_floor_corners
    )

    # Calibration State for Front View
    calibrating_front = False
    calibration_points = []

    def front_mouse_callback(event, x, y, flags, param):
        nonlocal calibration_points, calibrating_front
        if calibrating_front and event == cv2.EVENT_LBUTTONDOWN:
            h, w = param
            # Store as normalized [0, 1]
            calibration_points.append([x/w, y/h])
            print(f"[CALIB] Collected point {len(calibration_points)}/4: {x/w:.3f}, {y/h:.3f}")
            if len(calibration_points) >= 4:
                config.update_value("front_floor_corners", calibration_points)
                engine_front.floor_corners = calibration_points
                calibrating_front = False
                print("[SUCCESS] Front floor calibration saved!")

    cv2.namedWindow("VISION-AIR - FRONT View (Contact)")
    cv2.setMouseCallback("VISION-AIR - FRONT View (Contact)", front_mouse_callback, 
                         param=(270, 480)) # Default small window size for init
    
    # UI Setup
    ui_queue = Queue(maxsize=1)
    ui_process = Process(target=run_overlay_app, args=(config.desk_dims, ui_queue))
    ui_process.start()

    desk_view = np.zeros((config.desk_dims[1], config.desk_dims[0], 3), dtype=np.uint8)
    preview_enabled = True
    corrected_camera_feed = True

    print("[INFO] SYSTEM ONLINE. Move hands over desk to see tracking.")
    print("[CONTROLS] q=quit | h=toggle HID | v=toggle landmark preview | c=raw/corrected camera | t=swap X/Y | x=flip X | y=flip Y | r=reset axis correction")
    
    try:
        while True:
            ret_t, frame_top = cap_top.read()
            ret_f, frame_front = cap_front.read()
            
            if not ret_t:
                break
            
            # 1. Process Top View (X, Y)
            results_top = engine.process_frame(frame_top)
            
            # 2. Process Front View (Z/Contact)
            control_hand = get_right_hand(results_top)
            hand_desk_norm = None
            if control_hand:
                # Use current hand location to calculate expected floor height
                dx, dy, _ = control_hand['smooth']
                hand_desk_norm = (dx / config.desk_dims[0], dy / config.desk_dims[1])

            results_front = []
            if ret_f:
                # Initialize mouse callback with correct frame shape on first run
                cv2.setMouseCallback("VISION-AIR - FRONT View (Contact)", front_mouse_callback, 
                                     param=frame_front.shape[:2])
                results_front = engine_front.process_frame(frame_front, hand_desk_norm)

            desk_view.fill(15) 
            draw_desk_guides(desk_view, config.desk_dims)

            control_hand = get_right_hand(results_top)
            num_hands = len(results_top)
            mode = "MOUSE" if control_hand else ("KEYBOARD" if num_hands >= 2 else "IDLE")
            
            # Send to Transparent HUD
            ui_data = {
                'mode': mode,
                'hand_data': results_top,
                'kb_layout': layout if mode == "KEYBOARD" else None
            }
            if not ui_queue.full():
                ui_queue.put(ui_data)

            camera_view = frame_top.copy()
            camera_correction = config.axis_correction if corrected_camera_feed else None
            if camera_correction:
                camera_view = apply_axis_transform_to_image(camera_view, camera_correction)

            if mode == "MOUSE" and control_hand:
                hand = control_hand
                # Use the filtered desk coordinates calculated by the tracking engine.
                dx, dy, _ = hand['smooth']

                if hand.get('in_bounds', True) and hand.get('mouse_pose'):
                    hid.move_to(dx, dy)
                else:
                    hid.reset_cursor()
                    
                hid.update_click_state(False)

                tap_events = []
                tap_ready = hand.get('mouse_pose') or tap_manager.has_active_candidate()
                if hand.get('in_bounds', True) and tap_ready:
                    # Provide front-view contact results for fusion
                    tap_events = tap_manager.update(hand, engine, frame_top.shape, results_front)
                    for event in tap_events:
                        hid.click(event["button"])
                        color = (0, 255, 255) if event["button"] == "left" else (0, 140, 255)
                        point = (int(event["point"][0]), int(event["point"][1]))
                        cv2.circle(desk_view, point, 28, color, 3, cv2.LINE_AA)
                        cv2.putText(desk_view, event["button"].upper(), (point[0] + 12, point[1] - 12),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2, cv2.LINE_AA)
                else:
                    tap_manager.reset()
                
                # Visual Indicator (Debug View)
                # Use a solid Teal/Cyan circle for the cursor when in mouse mode
                color = (0, 210, 255)
                if not hand.get('in_bounds', True):
                    color = (0, 255, 255) # Yellow-ish for out of bounds
                cv2.circle(desk_view, (int(dx), int(dy)), 12, color, -1)

            elif mode == "KEYBOARD":
                hid.update_click_state(False)

                # Debug Keyboard View
                for key_name, rect in layout.keys.items():
                    x1 = int(rect[0] * config.desk_dims[0])
                    y1 = int(rect[1] * config.desk_dims[1])
                    x2 = int(rect[2] * config.desk_dims[0])
                    y2 = int(rect[3] * config.desk_dims[1])
                    cv2.rectangle(desk_view, (x1, y1), (x2, y2), (60, 60, 60), 1)
                
                for i, hand in enumerate(results_top[:2]):
                    # Detect taps on all fingertips
                    for tip_idx in [4, 8, 12, 16, 20]:
                        lm = hand['landmarks'][tip_idx]
                        dx, dy = engine.warp_point(lm.x, lm.y, frame_top.shape[1], frame_top.shape[0])
                        key = layout.get_key_at(dx, dy)
                        if key:
                            # Simple tap visual for now
                            cv2.circle(desk_view, (int(dx), int(dy)), 15, (0, 150, 255), 2)
                            # In full mode, collision_managers[i].check_collisions(hand['landmarks']) would inject keys
            else:
                hid.update_click_state(False)
                tap_manager.reset()
                hid.reset_cursor()

            if preview_enabled:
                for hand in results_top:
                    draw_hand_landmarks_on_camera(camera_view, hand, camera_correction)
                    draw_hand_landmarks_on_desk(desk_view, hand, engine, frame_top.shape)

            debug_hand = control_hand or (results_top[0] if results_top else None)
            tap_debug = tap_manager.debug_text()
            draw_debug_text(desk_view, mode, config, hid, debug_hand, tap_debug)
            draw_debug_text(camera_view, mode, config, hid, debug_hand, tap_debug)
            cv2.putText(camera_view, f"Top view: {'CORRECTED' if corrected_camera_feed else 'RAW'}",
                        (16, camera_view.shape[0] - 18), cv2.FONT_HERSHEY_SIMPLEX,
                        0.62, (0, 255, 255), 2, cv2.LINE_AA)

            cv2.imshow("VISION-AIR - TOP View", camera_view)
            cv2.imshow("VISION-AIR - Desk Map", desk_view)
            
            if ret_f:
                # Small debug monitor for front view
                front_small = cv2.resize(frame_front, (480, 270))
                sh, sw = front_small.shape[:2]
                
                # Draw desk plane on front view
                pts = np.array([[p[0]*sw, p[1]*sh] for p in engine_front.floor_corners], np.int32)
                cv2.polylines(front_small, [pts], True, (255, 0, 255), 2)
                
                if hand_desk_norm:
                    # Draw a dot at the expected floor point for the active finger
                    ex = int(hand_desk_norm[0] * sw)
                    ey = int(engine_front.get_expected_y(*hand_desk_norm) * sh)
                    cv2.circle(front_small, (ex, ey), 8, (0, 255, 255), -1)

                if calibrating_front:
                    cv2.putText(front_small, f"CALIBRATING: CLICK {4-len(calibration_points)} MORE", 
                                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                
                cv2.imshow("VISION-AIR - FRONT View (Contact)", front_small)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            if key in (ord('h'), ord('H')):
                hid.set_enabled(not hid.enabled)
            elif key in (ord('v'), ord('V')):
                preview_enabled = not preview_enabled
                print(f"[PREVIEW] Landmark preview {'enabled' if preview_enabled else 'disabled'}")
            elif key in (ord('c'), ord('C')):
                corrected_camera_feed = not corrected_camera_feed
                print(f"[CAMERA] View {'corrected' if corrected_camera_feed else 'raw'}")
            elif key in (ord('t'), ord('T'), ord('x'), ord('X'), ord('y'), ord('Y'), ord('r'), ord('R')):
                toggle_axis(config, key)
            elif key == ord('['):
                new_floor = max(0.1, config.desk_y_floor - 0.005)
                config.update_value("desk_y_floor", new_floor)
                engine_front.desk_y_floor = new_floor
                print(f"[CALIB] Floor moved UP to {new_floor:.3f}")
            elif key == ord(']'):
                new_floor = min(1.0, config.desk_y_floor + 0.005)
                config.update_value("desk_y_floor", new_floor)
                engine_front.desk_y_floor = new_floor
                print(f"[CALIB] Floor moved DOWN to {new_floor:.3f}")
            elif key == ord('f'):
                calibrating_front = True
                calibration_points = []
                print("[INFO] Click 4 corners of the desk in FRONT VIEW: TL, TR, BR, BL")
    except Exception as e:
        print(f"[FATAL RUNTIME ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        cap_top.release()
        cap_front.release()
        cv2.destroyAllWindows()
        if 'ui_process' in locals():
            ui_process.terminate()
        if 'hid' in locals():
            hid.release_buttons()
        print("[INFO] Shutdown cleanup complete.")
        input("Press Enter to quit.")

if __name__ == "__main__":
    main()
