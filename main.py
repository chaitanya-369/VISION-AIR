import cv2
import numpy as np
from tracking_engine import TrackingEngine

def main():
    try:
        engine = TrackingEngine()
    except Exception as e:
        print(f"Initialization failed: {e}")
        print("Please run calibration.py first.")
        return

    cap = cv2.VideoCapture(engine.camera_index)
    
    desk_w, desk_h = engine.desk_dims
    desk_view = np.zeros((desk_h, desk_w, 3), dtype=np.uint8)

    print("VISION-AIR Phase 1: Tracking Demo")
    print("Press 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Process frame
        results = engine.process_frame(frame)
        
        # Clear desk view
        desk_view.fill(20) # Dark gray background

        # Draw grid on desk view for reference
        for i in range(0, desk_w, 100):
            cv2.line(desk_view, (i, 0), (i, desk_h), (50, 50, 50), 1)
        for i in range(0, desk_h, 100):
            cv2.line(desk_view, (0, i), (desk_w, i), (50, 50, 50), 1)

        for hand in results:
            # Draw on original frame (MediaPipe built-in)
            engine.mp_draw.draw_landmarks(frame, hand['landmarks'], engine.mp_hands.HAND_CONNECTIONS)
            
            # Draw smoothed point on desk view
            sx, sy, sz = hand['smooth']
            
            # Clamp to desk dimensions
            sx = int(np.clip(sx, 0, desk_w))
            sy = int(np.clip(sy, 0, desk_h))
            
            # Visualize Z (Depth) as circle size
            # sz is relative depth. Values around -0.1 to 0.1 usually.
            # Convert to radius: closer (more negative) = larger circle
            radius = int(max(5, 20 - (sz * 100)))
            
            cv2.circle(desk_view, (sx, sy), radius, (0, 255, 0), -1)
            cv2.putText(desk_view, f"Z: {sz:.2f}", (sx + 10, sy + 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # Show both windows
        cv2.imshow("Camera View (Raw + MediaPipe)", frame)
        cv2.imshow("Warped Desk View (Smoothed)", desk_view)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
