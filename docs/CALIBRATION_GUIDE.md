# Calibration Guide: VISION-AIR

Proper calibration is essential for accurate spatial tracking. Follow these steps to set up your environment.

## 1. Camera Placement
- **Top Camera**: Should be placed directly above the desk area, looking straight down (Nadir view). Ensure the camera is stable and tidak bergoyang (low vibration).
- **Lighting**: Bright, even lighting is best. Avoid strong backlighting or shadows falling across the desk area.

## 2. Overhead Calibration (Desk Mapping)
Run the following script:
```bash
python scripts/calibrate.py
```
1. A window will open showing the camera feed.
2. Click the four corners of your workspace in the following order:
   - **Top-Left (TL)**
   - **Top-Right (TR)**
   - **Bottom-Right (BR)**
   - **Bottom-Left (BL)**
3. Press `S` to save and exit.
4. The system will generate a `config.json` containing the homography matrix.

## 3. Floor-Line Calibration (Optional Front View)
If you are using a secondary front-facing camera for click detection:
1. Run the main system: `python -m vision_air.main`
2. Press `F` to enter Front-View Calibration.
3. Click the 4 corners of the desk boundary *as seen from the front camera*.
4. This allows the system to calculate the "ground plane" for different finger positions.

## 4. Fine-Tuning
Once the system is running, use these keys for real-time adjustments:
- `[` and `]`: Move the virtual "floor" up or down globally. Use this if the system is clicking too easily or not clicking at all.
- `T`: Swap X and Y axes if the movement is rotated.
- `X / Y`: Invert axes if movement is mirrored.
