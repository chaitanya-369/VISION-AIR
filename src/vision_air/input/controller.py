from pynput.mouse import Button, Controller as MouseController
import pyautogui
import numpy as np

class HIDController:
    def __init__(self, desk_dims):
        self.mouse = MouseController()
        self.desk_w, self.desk_h = desk_dims
        self.screen_w, self.screen_h = pyautogui.size()
        
        self.is_pinched = False
        print(f"HIDController initialized. Mapping {desk_dims} desk to {self.screen_w}x{self.screen_h} screen.")

    def map_absolute(self, desk_x, desk_y):
        # Map desk [0, W] to screen [0, W_s]
        screen_x = (desk_x / self.desk_w) * self.screen_w
        screen_y = (desk_y / self.desk_h) * self.screen_h
        
        # Clamp to screen bounds
        screen_x = int(np.clip(screen_x, 0, self.screen_w - 1))
        screen_y = int(np.clip(screen_y, 0, self.screen_h - 1))
        
        return screen_x, screen_y

    def move_to(self, desk_x, desk_y):
        screen_x, screen_y = self.map_absolute(desk_x, desk_y)
        self.mouse.position = (screen_x, screen_y)

    def update_click_state(self, pinch_active):
        if pinch_active and not self.is_pinched:
            # Pinch started -> Press
            self.mouse.press(Button.left)
            self.is_pinched = True
            print("Mouse Press")
        elif not pinch_active and self.is_pinched:
            # Pinch released -> Release
            self.mouse.release(Button.left)
            self.is_pinched = False
            print("Mouse Release")
