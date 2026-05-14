import os
import gdown

MODEL_PATH = "backend/ml/model.pt"

# ensure folder exists
os.makedirs("backend/ml", exist_ok=True)

if not os.path.exists(MODEL_PATH):
    print("Downloading model...")
    url = "https://drive.google.com/file/d/1zp2qZBzaiRi-qjWdDGg8905jfneKVdw3/view?usp=drive_link"
    gdown.download(url, MODEL_PATH, quiet=False)
else:
    print("Model already exists")