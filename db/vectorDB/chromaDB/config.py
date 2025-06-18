"""
ChromaDB 설정 관리
"""

import base64
import os
from typing import Any, Dict

from dotenv import load_dotenv


class ChromaDBConfig:
    """ChromaDB 설정 클래스"""

    def __init__(self, config_file: str = ".env.chromadb"):
        """
        설정 초기화

        Args:
            config_file: 환경 변수 파일 경로
        """
        # 환경 변수 로드
        load_dotenv(config_file, override=True)

        # 원격 서버 설정
        self.remote_url = os.getenv(
            "CHROMADB_URL", "https://chromadb-1.skala25a.project.skala-ai.com"
        )
        self.username = os.getenv("CHROMADB_USERNAME", "skala")
        self.password = os.getenv("CHROMADB_PASSWORD", "Skala25a!23$")
        self.use_remote = os.getenv("USE_REMOTE_CHROMADB", "true").lower() == "true"

        # 로컬 설정
        self.local_path = os.getenv("LOCAL_CHROMADB_PATH", "chroma_data")

        # 임베딩 설정
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "BAAI/bge-base-en")

        # Basic Auth 헤더 생성
        self.auth_header = self._generate_auth_header()

    def _generate_auth_header(self) -> str:
        """Basic Auth 헤더 생성"""
        auth_string = f"{self.username}:{self.password}"
        auth_bytes = auth_string.encode("ascii")
        auth_b64 = base64.b64encode(auth_bytes).decode("ascii")
        return f"Basic {auth_b64}"

    def get_remote_config(self) -> Dict[str, Any]:
        """원격 연결 설정 반환"""
        from urllib.parse import urlparse

        parsed = urlparse(self.remote_url)

        return {
            "host": parsed.hostname,
            "port": parsed.port or (443 if parsed.scheme == "https" else 80),
            "ssl": parsed.scheme == "https",
            "headers": {"Authorization": self.auth_header},
        }

    def get_local_config(self) -> Dict[str, Any]:
        """로컬 연결 설정 반환"""
        # 절대 경로로 변환
        if not os.path.isabs(self.local_path):
            self.local_path = os.path.join(os.getcwd(), self.local_path)

        os.makedirs(self.local_path, exist_ok=True)

        return {"path": self.local_path}

    def __str__(self) -> str:
        return f"ChromaDBConfig(remote={self.use_remote}, url={self.remote_url})"


# 전역 설정 인스턴스
_config = None


def get_config() -> ChromaDBConfig:
    """전역 설정 인스턴스 반환"""
    global _config
    if _config is None:
        _config = ChromaDBConfig()
    return _config
