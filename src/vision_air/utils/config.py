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
