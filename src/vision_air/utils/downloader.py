import os
import urllib.request
from tqdm import tqdm

MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "assets", "models", "hand_landmarker.task")

def download_model():
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    
    if os.path.exists(MODEL_PATH):
        print(f"[INFO] Model already exists at {MODEL_PATH}")
        return True

    print(f"[INFO] Downloading MediaPipe Hand Landmarker model to {MODEL_PATH}...")
    try:
        class DownloadProgressBar(tqdm):
            def update_to(self, b=1, bsize=1, tsize=None):
                if tsize is not None:
                    self.total = tsize
                self.update(b * bsize - self.n)

        with DownloadProgressBar(unit='B', unit_scale=True, miniters=1, desc=MODEL_URL.split('/')[-1]) as t:
            urllib.request.urlretrieve(MODEL_URL, filename=MODEL_PATH, reporthook=t.update_to)
        print("[SUCCESS] Model downloaded successfully.")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to download model: {e}")
        # Workaround if tqdm is not installed or errors
        try:
            print("[INFO] Attempting download without progress bar...")
            urllib.request.urlretrieve(MODEL_URL, filename=MODEL_PATH)
            print("[SUCCESS] Model downloaded successfully.")
            return True
        except Exception as e2:
            print(f"[FATAL] Fallback download also failed: {e2}")
            return False

if __name__ == "__main__":
    download_model()
