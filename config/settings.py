import os

from dotenv import load_dotenv

# 로컬 개발 환경이면 .env 로드
if os.getenv("ENV", "local") == "local":
    load_dotenv(override=True)


class Settings:
    def __init__(self):
        # 환경 정보
        self.env = os.getenv("ENV", "local")
        self.debug = self.env == "local"

        # OpenAI API 키 (Kubernetes Secret 또는 .env)
        self.api_key = os.getenv("OPENAI_API_KEY")

        self.subjective_grader_model = os.getenv("AGENT_SUBJECTIVE_GRADER_MODEL")

        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.google_cse_id = os.getenv("GOOGLE_CSE_ID")

        # Redis 설정
        self.redis_host = os.getenv("REDIS_HOST", "localhost")
        self.redis_port = int(os.getenv("REDIS_PORT", "6379"))
        self.redis_db = int(os.getenv("REDIS_DB", "0"))
        self.redis_password = os.getenv("REDIS_PASSWORD", None)

        # 경로 설정
        self.BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # config/
        self.ROOT_DIR = os.path.abspath(os.path.join(self.BASE_DIR, ".."))  # SKIB-AI/
        self.DATA_DIR = os.path.join(self.ROOT_DIR, "data")  # SKIB-AI/data/
        self.DOCUMENT_UPLOAD_DIR = os.path.join(
            self.DATA_DIR, "documents"
        )  # SKIB-AI/data/documents/
        self.GLOBAL_DIR = os.path.join(
            self.DOCUMENT_UPLOAD_DIR, "global"
        )  # SKIB-AI/data/documents/global/
        self.PROJECT_DIR_BASE = os.path.join(
            self.DOCUMENT_UPLOAD_DIR, "projects"
        )  # SKIB-AI/data/documents/projects/

        # ChromaDB 저장 경로
        self.CHROMA_DIR = os.path.join(self.DATA_DIR, "chroma_data")


settings = Settings()
