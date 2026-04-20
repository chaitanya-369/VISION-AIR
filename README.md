# VISION-AIR (Virtual Spatial Interface)

This project transforms any flat surface (desk) into a high-precision, multi-functional input device using only a standard overhead webcam.

## Features
- **Invisible UI**: Automatically switches between keyboard and gesture mouse modes.
- **Perspective Correction**: Homography-based mapping for linear movement.
- **Delta-Z Algorithm**: Depth velocity detection for virtual "collision" events (clicks/taps).
- **One-Euro Filter**: Jitter-free, fluid cursor movement.

## Tech Stack
- Python 3.10+
- OpenCV (cv2)
- MediaPipe
- NumPy
- pynput / PyAutoGUI

## Installation
```bash
pip install -r requirements.txt
```

## Hardware Target
- Intel i5-8500T
- Integrated Graphics
- Standard Overhead Webcam (Nadir View)
