import os

# 현재 파일 기준 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # config/
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))  # SKIB-AI/

# 업로드 디렉토리 설정
DATA_DIR = os.path.join(ROOT_DIR, "data")  # SKIB-AI/data/
DOCUMENT_UPLOAD_DIR = os.path.join(DATA_DIR, "documents")  # SKIB-AI/documents/
GLOBAL_DIR = os.path.join(DOCUMENT_UPLOAD_DIR, "global")  # SKIB-AI/documents/global/
PROJECT_DIR_BASE = os.path.join(
    DOCUMENT_UPLOAD_DIR, "projects"
)  # SKIB-AI/documents/projects/
