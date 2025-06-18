"""
ChromaDB 클라이언트 연결 및 관리
"""

import chromadb
from chromadb import Settings
from chromadb.config import Settings as ChromaSettings
from typing import Optional, Union
import logging

from .config import get_config

logger = logging.getLogger(__name__)


class ChromaDBClient:
    """ChromaDB 클라이언트 래퍼 클래스"""
    
    def __init__(self, force_local: bool = False):
        """
        ChromaDB 클라이언트 초기화
        
        Args:
            force_local: 강제로 로컬 클라이언트 사용
        """
        self.config = get_config()
        self.client = None
        self.is_remote = False
        
        if not force_local and self.config.use_remote:
            self.is_remote = self._connect_remote()
        
        if not self.is_remote:
            self._connect_local()
    
    def _connect_remote(self) -> bool:
        """원격 ChromaDB 서버에 연결"""
        logger.info("🔄 원격 ChromaDB 서버 연결 시도")
        
        try:
            remote_config = self.config.get_remote_config()
            
            self.client = chromadb.HttpClient(
                **remote_config,
                settings=ChromaSettings(anonymized_telemetry=False)
            )
            
            # 연결 테스트
            heartbeat = self.client.heartbeat()
            logger.info(f"✅ 원격 ChromaDB 연결 성공: {heartbeat}")
            
            return True
            
        except Exception as e:
            logger.warning(f"❌ 원격 연결 실패: {e}")
            return False
    
    def _connect_local(self):
        """로컬 ChromaDB에 연결"""
        logger.info("📂 로컬 ChromaDB 연결")
        
        try:
            local_config = self.config.get_local_config()
            
            self.client = chromadb.PersistentClient(
                path=local_config["path"],
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            logger.info(f"✅ 로컬 ChromaDB 연결 성공: {local_config['path']}")
            
        except Exception as e:
            logger.error(f"❌ 로컬 ChromaDB 연결 실패: {e}")
            raise
    
    def get_client(self):
        """ChromaDB 클라이언트 반환"""
        return self.client
    
    def test_connection(self) -> bool:
        """연결 테스트"""
        try:
            heartbeat = self.client.heartbeat()
            logger.info(f"💓 Heartbeat: {heartbeat}")
            
            # 버전 정보
            try:
                version = self.client.get_version()
                logger.info(f"🔖 ChromaDB 버전: {version}")
            except:
                logger.warning("⚠️ 버전 정보 조회 실패")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 연결 테스트 실패: {e}")
            return False
    
    def get_info(self) -> dict:
        """클라이언트 정보 반환"""
        return {
            "is_remote": self.is_remote,
            "server_url": self.config.remote_url if self.is_remote else "local",
            "local_path": self.config.local_path if not self.is_remote else None,
            "embedding_model": self.config.embedding_model
        }


# 전역 클라이언트 인스턴스
_client = None

def get_client(force_local: bool = False) -> ChromaDBClient:
    """
    전역 ChromaDB 클라이언트 반환
    
    Args:
        force_local: 강제로 로컬 클라이언트 사용
        
    Returns:
        ChromaDBClient 인스턴스
    """
    global _client
    if _client is None or force_local:
        _client = ChromaDBClient(force_local=force_local)
    return _client


def reset_client():
    """클라이언트 재설정"""
    global _client
    _client = None