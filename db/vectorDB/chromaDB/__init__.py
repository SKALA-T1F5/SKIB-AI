"""
ChromaDB 벡터 데이터베이스 모듈

이 모듈은 ChromaDB를 사용한 벡터 저장, 검색, 관리 기능을 제공합니다.

주요 구성요소:
- client.py: ChromaDB 클라이언트 연결 및 설정
- upload.py: 문서 업로드 및 임베딩 생성
- search.py: 벡터 검색 및 유사도 검색
- utils.py: 유틸리티 함수들
- config.py: 설정 관리
"""

from .client import ChromaDBClient, get_client
from .config import ChromaDBConfig
from .delete import (
    delete_empty_collections,
    delete_multiple_collections,
    delete_test_collections,
    get_deletion_preview,
    interactive_delete,
    show_deletion_preview,
)
from .search import search_by_metadata, search_similar
from .upload import batch_upload, upload_chunks, upload_documents
from .utils import delete_collection, get_collection_info, list_collections

__all__ = [
    "ChromaDBClient",
    "get_client",
    "upload_documents",
    "upload_chunks",
    "batch_upload",
    "search_similar",
    "search_by_metadata",
    "list_collections",
    "get_collection_info",
    "delete_collection",
    "delete_multiple_collections",
    "delete_empty_collections",
    "delete_test_collections",
    "get_deletion_preview",
    "show_deletion_preview",
    "interactive_delete",
    "ChromaDBConfig",
]

__version__ = "1.0.0"
