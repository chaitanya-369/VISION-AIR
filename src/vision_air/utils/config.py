import json
import os
import numpy as np

class ConfigManager:
    def __init__(self, config_path="config.json"):
        self.config_path = config_path
        self.config = {}

    def load(self):
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Configuration file not found at {self.config_path}. Please run calibration.")
        
        with open(self.config_path, "r") as f:
            self.config = json.load(f)
        return self.config

    def save(self, data):
        with open(self.config_path, "w") as f:
            json.dump(data, f, indent=4)
        self.config = data

    def update_value(self, key, value):
        self.config[key] = value
        self.save(self.config)

    @property
    def homography_matrix(self):
        if not self.config:
            self.load()
        return np.array(self.config["homography_matrix"])

    @property
    def camera_index(self):
        if not self.config:
            self.load()
        return self.config.get("camera_index", 0)

    @property
    def desk_dims(self):
        if not self.config:
            self.load()
        return self.config["desk_dims"]

    @property
    def axis_correction(self):
        if not self.config:
            self.load()
        return self.config.get(
            "axis_correction",
            {"swap_xy": False, "invert_x": False, "invert_y": False},
        )

    @property
    def camera_front_index(self):
        if not self.config:
            self.load()
        return self.config.get("camera_front_index", 1)

    @property
    def desk_y_floor(self):
        if not self.config:
            self.load()
        return self.config.get("desk_y_floor", 0.8)

    @property
    def front_floor_corners(self):
        if not self.config:
            self.load()
        return self.config.get("front_floor_corners", [
            [0.0, 0.8], [1.0, 0.8], [1.0, 0.9], [0.0, 0.9]
        ])
