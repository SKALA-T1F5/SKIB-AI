"""
ChromaDB 유틸리티 함수들
"""

from typing import List, Dict, Any, Optional
import logging

from .client import get_client

logger = logging.getLogger(__name__)


def create_or_get_collection(collection_name: str, client=None, recreate: bool = False):
    """
    컬렉션 생성 또는 가져오기
    
    Args:
        collection_name: 컬렉션 이름
        client: ChromaDB 클라이언트 (None이면 기본 클라이언트 사용)
        recreate: 기존 컬렉션 삭제 후 재생성 여부
        
    Returns:
        ChromaDB Collection 객체
    """
    if client is None:
        client = get_client().get_client()
    
    try:
        if recreate:
            try:
                client.delete_collection(name=collection_name)
                logger.info(f"🗑️ 기존 컬렉션 '{collection_name}' 삭제됨")
            except Exception:
                pass  # 컬렉션이 없으면 무시
        
        # 컬렉션 생성 또는 가져오기
        collection = client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        
        logger.debug(f"✅ 컬렉션 '{collection_name}' 준비 완료")
        return collection
        
    except Exception as e:
        logger.error(f"❌ 컬렉션 생성/조회 실패: {e}")
        raise


def list_collections() -> List[str]:
    """
    모든 컬렉션 목록 조회
    
    Returns:
        컬렉션 이름 리스트
    """
    try:
        client = get_client().get_client()
        collections = client.list_collections()
        collection_names = [col.name for col in collections]
        
        logger.debug(f"📂 컬렉션 목록: {len(collection_names)}개")
        return collection_names
        
    except Exception as e:
        logger.error(f"❌ 컬렉션 목록 조회 실패: {e}")
        return []


def get_collection_info(collection_name: str) -> Dict[str, Any]:
    """
    컬렉션 정보 조회
    
    Args:
        collection_name: 컬렉션 이름
        
    Returns:
        컬렉션 정보 딕셔너리
    """
    try:
        collection = create_or_get_collection(collection_name)
        data = collection.get()
        
        # 메타데이터 통계
        metadata_stats = {}
        if data['metadatas']:
            # 타입별 통계
            type_counts = {}
            source_counts = {}
            
            for metadata in data['metadatas']:
                if metadata:
                    chunk_type = metadata.get('chunk_type', 'unknown')
                    source = metadata.get('source', 'unknown')
                    
                    type_counts[chunk_type] = type_counts.get(chunk_type, 0) + 1
                    source_counts[source] = source_counts.get(source, 0) + 1
            
            metadata_stats = {
                "types": type_counts,
                "sources": source_counts
            }
        
        info = {
            "name": collection_name,
            "count": len(data['ids']),
            "metadata": collection.metadata,
            "sample_ids": data['ids'][:5] if data['ids'] else [],
            "stats": metadata_stats
        }
        
        logger.debug(f"📊 컬렉션 '{collection_name}' 정보: {info['count']}개 문서")
        return info
        
    except Exception as e:
        logger.error(f"❌ 컬렉션 정보 조회 실패: {e}")
        return {}


def delete_collection(collection_name: str) -> bool:
    """
    컬렉션 삭제
    
    Args:
        collection_name: 컬렉션 이름
        
    Returns:
        삭제 성공 여부
    """
    try:
        client = get_client().get_client()
        client.delete_collection(name=collection_name)
        logger.info(f"🗑️ 컬렉션 '{collection_name}' 삭제됨")
        return True
        
    except Exception as e:
        logger.error(f"❌ 컬렉션 삭제 실패: {e}")
        return False


def clear_collection(collection_name: str) -> bool:
    """
    컬렉션 내용 모두 삭제 (컬렉션은 유지)
    
    Args:
        collection_name: 컬렉션 이름
        
    Returns:
        삭제 성공 여부
    """
    try:
        collection = create_or_get_collection(collection_name)
        
        # 모든 문서 ID 가져오기
        data = collection.get()
        if data['ids']:
            collection.delete(ids=data['ids'])
            logger.info(f"🧹 컬렉션 '{collection_name}' 내용 삭제: {len(data['ids'])}개")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 컬렉션 내용 삭제 실패: {e}")
        return False


def get_collection_stats() -> Dict[str, Any]:
    """
    전체 ChromaDB 통계 정보
    
    Returns:
        통계 정보 딕셔너리
    """
    try:
        collections = list_collections()
        total_documents = 0
        collection_stats = {}
        
        for collection_name in collections:
            info = get_collection_info(collection_name)
            collection_stats[collection_name] = {
                "count": info.get("count", 0),
                "types": info.get("stats", {}).get("types", {}),
                "sources": info.get("stats", {}).get("sources", {})
            }
            total_documents += info.get("count", 0)
        
        client_info = get_client().get_info()
        
        stats = {
            "total_collections": len(collections),
            "total_documents": total_documents,
            "collections": collection_stats,
            "client_info": client_info
        }
        
        logger.info(f"📈 ChromaDB 통계: {len(collections)}개 컬렉션, {total_documents}개 문서")
        return stats
        
    except Exception as e:
        logger.error(f"❌ 통계 조회 실패: {e}")
        return {}


def test_connection() -> bool:
    """ChromaDB 연결 테스트"""
    try:
        client = get_client()
        return client.test_connection()
    except Exception as e:
        logger.error(f"❌ 연결 테스트 실패: {e}")
        return False


def reset_all() -> bool:
    """모든 컬렉션 삭제 (주의!)"""
    try:
        collections = list_collections()
        deleted_count = 0
        
        for collection_name in collections:
            if delete_collection(collection_name):
                deleted_count += 1
        
        logger.warning(f"🗑️ 모든 컬렉션 삭제 완료: {deleted_count}/{len(collections)}개")
        return deleted_count == len(collections)
        
    except Exception as e:
        logger.error(f"❌ 전체 삭제 실패: {e}")
        return False