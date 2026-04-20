# Technical Architecture: VISION-AIR

This document details the internal workings of the VISION-AIR system.

## 1. Vision Pipeline

The system uses a hierarchical processing model to transform pixel data into spatial coordinates.

### Tracking Engine (`src/vision_air/core/tracking.py`)
- **MediaPipe Hand Landmarker**: Utilizes the Google MediaPipe framework to detect 21 hand landmarks in real-time.
- **ROI Optimization**: Dynamically crops the camera frame around detected hands to reduce processing load in subsequent frames (temporal consistency).

### Delta-Z Algorithm (`src/vision_air/core/collision_detector.py`)
Since standard webcams lack depth sensors, VISION-AIR uses a "Delta-Z" heuristic:
1. **Vertical Velocity**: Tracks the Z-coordinate (normalized landmark depth) and its first derivative ($dZ/dt$).
2. **Impact Detection**: A sudden spike in negative acceleration ($d^2Z/dt^2$) when the fingertip is near the desk plane signals a "tap".
3. **Contact Verification**: Fuses data from the `FrontEngine` when available to confirm physical proximity to the desk surface.

## 2. Spatial Mapping

### Homography Transformation
The system maps the camera's perspective view to a flat 2D coordinate system (the "Desk Space").
- **4-Point Calibration**: The user defines the physical boundaries of the desk.
- **Bilinear Warp**: A perspective transform matrix is calculated to project any point $(x, y)$ from the camera frame to $(u, v)$ in desk-normalized coordinates.

### Movement Filtering
To eliminate camera jitter and hand tremors, a **One-Euro Filter** is applied. This filter uses a frequency-dependent cutoff:
- Low speed -> Strong filtering (avoids jitter during precision tasks).
- High speed -> Low filtering (avoids lag during rapid movement).

## 3. Human-Machine Interface (HMI)

### HID Controller (`src/vision_air/input/controller.py`)
- **Bridge**: Translates desk coordinates into OS-level mouse/keyboard events using `pynput` and `pyautogui`.
- **Safety Switch**: A global `enabled` flag (toggled by the 'H' key) prevents accidental inputs while the system is initializing.

### UI Overlay (`src/vision_air/ui/overlay.py`)
- **Transparent HUD**: A PyQt5-based top-level window that provides real-time feedback.
- **Visual Cues**: Displays different colors for "Mouse Mode" (Single Hand) vs "Keyboard Mode" (Dual Hand).

## 4. Multi-Camera Fusion (Beta)

The `FrontEngine` uses a secondary camera placed flat on the desk.
- **Floor-Line Masking**: Detects the boundary where fingers "touch" their own reflection on the desk.
- **Zero-Tolerance Detection**: By observing the distance between the fingertip and the floor-line, the system achieves near 100% accuracy for physical desk taps.
