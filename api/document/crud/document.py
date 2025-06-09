import os
from pathlib import Path
from config.settings import UPLOAD_DIR

def save_file_locally(file, filename: str) -> str:
    Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    file_path = os.path.join(UPLOAD_DIR, filename)
    with open(file_path, "wb") as f:
        f.write(file)
    return file_path
