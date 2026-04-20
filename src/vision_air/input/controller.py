from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Controller as KeyboardController
import pyautogui
import numpy as np
import winsound # For audio feedback proxy

class HIDController:
    def __init__(self, desk_dims):
        self.mouse = MouseController()
        self.keyboard = KeyboardController()
        self.desk_w, self.desk_h = desk_dims
        self.screen_w, self.screen_h = pyautogui.size()
        
        self.is_pressed = False
        self.enabled = True
        
        # Physics State
        self.last_desk_pos = None
        self.sensitivity = 1.2
        self.accel_exponent = 1.15 # Curve for mouse acceleration
        self.min_delta = 0.5        # Sub-pixel threshold
        
        print(f"HIDController initialized (Relative Mode). Sensitivity: {self.sensitivity}")

    def type_key(self, char):
        if char:
            self.keyboard.press(char)
            self.keyboard.release(char)
            # Proxy audio feedback: 2000Hz for 10ms
            winsound.Beep(2000, 10)
            print(f"Typed: {char}")

    def map_absolute(self, desk_x, desk_y):
        # Map desk [0, W] to screen [0, W_s]
        screen_x = (desk_x / self.desk_w) * self.screen_w
        screen_y = (desk_y / self.desk_h) * self.screen_h
        
        # Clamp to screen bounds
        screen_x = int(np.clip(screen_x, 0, self.screen_w - 1))
        screen_y = int(np.clip(screen_y, 0, self.screen_h - 1))
        
        return screen_x, screen_y

    def move_to(self, desk_x, desk_y):
        """
        Processes a desk coordinate as a relative displacement for the mouse.
        """
        if not self.enabled:
            return
            
        if self.last_desk_pos is None:
            self.last_desk_pos = (desk_x, desk_y)
            return

        # 1. Calculate displacement in desk units
        dx = desk_x - self.last_desk_pos[0]
        dy = desk_y - self.last_desk_pos[1]
        self.last_desk_pos = (desk_x, desk_y)

        # 2. Scale to screen pixels (Approximate 1:1 at base sensitivity)
        # We use desk_w as a normalization factor
        px_x = (dx / self.desk_w) * self.screen_w * self.sensitivity
        px_y = (dy / self.desk_h) * self.screen_h * self.sensitivity
        
        dist = np.sqrt(px_x**2 + px_y**2)
        if dist < self.min_delta:
            return

        # 3. Apply Mouse Acceleration Curve
        # Formula: pixel_delta = base_delta * (distance ^ curve)
        # Low distance -> base delta (precise)
        # High distance -> magnified delta (fast)
        accel = (dist ** self.accel_exponent) / (dist if dist > 0 else 1)
        
        final_dx = px_x * accel
        final_dy = px_y * accel

        # 4. Inject relative movement
        self.mouse.move(int(final_dx), int(final_dy))

    def reset_cursor(self):
        """Clears the reference position (used when hand is lifted)."""
        self.last_desk_pos = None

    def update_click_state(self, button_active):
        if not self.enabled:
            self.release_buttons()
            return

        if button_active and not self.is_pressed:
            # Click started -> Press
            self.mouse.press(Button.left)
            self.is_pressed = True
            print("Mouse Press")
        elif not button_active and self.is_pressed:
            # Click released -> Release
            self.mouse.release(Button.left)
            self.is_pressed = False
            print("Mouse Release")

    def click(self, button_name):
        if not self.enabled:
            return

        self.release_buttons()
        button = Button.right if button_name == "right" else Button.left
        self.mouse.click(button, 1)
        print(f"Mouse {button_name.title()} Click")

    def release_buttons(self):
        if self.is_pressed:
            self.mouse.release(Button.left)
            self.is_pressed = False
            print("Mouse Release")

    def set_enabled(self, enabled):
        self.enabled = enabled
        if not enabled:
            self.release_buttons()
            self.last_desk_pos = None
        print(f"HID {'enabled' if enabled else 'disabled'}")
