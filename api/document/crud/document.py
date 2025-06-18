import hashlib
import os
from shutil import copyfile

from config.settings import settings  # 변경된 경로 사용


def compute_file_hash(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


def save_document_locally(
    file_bytes: bytes, document_id: str, project_id: str, name: str
) -> dict:
    file_hash = compute_file_hash(file_bytes)

    global_path = os.path.join(settings.GLOBAL_DIR, f"{file_hash}.pdf")
    project_dir = os.path.join(settings.PROJECT_DIR_BASE, project_id)
    os.makedirs(project_dir, exist_ok=True)
    project_path = os.path.join(project_dir, f"{document_id}_{name}.pdf")

    # Step 1: global 저장
    if not os.path.exists(global_path):
        os.makedirs(settings.GLOBAL_DIR, exist_ok=True)
        with open(global_path, "wb") as f:
            f.write(file_bytes)

    # Step 2: 프로젝트 링크 생성
    if not os.path.exists(project_path):
        try:
            os.symlink(os.path.abspath(global_path), project_path)
        except Exception:
            copyfile(global_path, project_path)

    return {
        "file_hash": file_hash,
        "global_path": global_path,
        "project_path": project_path,
    }
