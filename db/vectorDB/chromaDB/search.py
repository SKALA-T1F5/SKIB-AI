"""
ChromaDB 벡터 검색 및 유사도 검색
"""

import logging
from typing import Any, Dict, List, Optional

from sentence_transformers import SentenceTransformer

from .client import get_client
from .utils import create_or_get_collection

logger = logging.getLogger(__name__)


class ChromaDBSearcher:
    """ChromaDB 검색 관리 클래스"""

    def __init__(self, embedding_model: str = "BAAI/bge-base-en"):
        """
        검색기 초기화

        Args:
            embedding_model: 임베딩 모델명
        """
        self.client = get_client()
        self.embedding_model = SentenceTransformer(embedding_model)
        logger.info(f"🔍 검색 모델 로드: {embedding_model}")

    def search_similar(
        self,
        query: str,
        collection_name: str,
        n_results: int = 5,
        where: Dict[str, Any] = None,
        where_document: Dict[str, Any] = None,
    ) -> List[Dict[str, Any]]:
        """
        유사도 검색

        Args:
            query: 검색 쿼리
            collection_name: 컬렉션 이름
            n_results: 반환할 결과 수
            where: 메타데이터 필터
            where_document: 문서 내용 필터

        Returns:
            검색 결과 리스트
        """
        try:
            collection = create_or_get_collection(
                collection_name, self.client.get_client()
            )

            # 쿼리 임베딩 생성
            query_embedding = self.embedding_model.encode(query).tolist()

            # 검색 실행
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where,
                where_document=where_document,
                include=["documents", "metadatas", "distances"],
            )

            # 결과 변환
            search_results = []
            if results["documents"] and results["documents"][0]:
                for i in range(len(results["documents"][0])):
                    result = {
                        "content": results["documents"][0][i],
                        "metadata": (
                            results["metadatas"][0][i] if results["metadatas"] else {}
                        ),
                        "distance": (
                            results["distances"][0][i] if results["distances"] else 0.0
                        ),
                        "similarity": (
                            1 - results["distances"][0][i]
                            if results["distances"]
                            else 1.0
                        ),
                        "id": results["ids"][0][i] if results["ids"] else None,
                    }
                    search_results.append(result)

            logger.debug(f"🔍 검색 완료: {len(search_results)}개 결과")
            return search_results

        except Exception as e:
            logger.error(f"❌ 검색 실패: {e}")
            return []

    def search_by_metadata(
        self,
        collection_name: str,
        where: Dict[str, Any],
        n_results: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        메타데이터 기반 검색

        Args:
            collection_name: 컬렉션 이름
            where: 메타데이터 필터
            n_results: 반환할 결과 수 (None이면 모든 결과)

        Returns:
            검색 결과 리스트
        """
        try:
            collection = create_or_get_collection(
                collection_name, self.client.get_client()
            )

            # 메타데이터 기반 검색
            results = collection.get(
                where=where, limit=n_results, include=["documents", "metadatas"]
            )

            # 결과 변환
            search_results = []
            if results["documents"]:
                for i in range(len(results["documents"])):
                    result = {
                        "content": results["documents"][i],
                        "metadata": (
                            results["metadatas"][i] if results["metadatas"] else {}
                        ),
                        "id": results["ids"][i] if results["ids"] else None,
                    }
                    search_results.append(result)

            logger.debug(f"📋 메타데이터 검색 완료: {len(search_results)}개 결과")
            return search_results

        except Exception as e:
            logger.error(f"❌ 메타데이터 검색 실패: {e}")
            return []

    def search_by_source(
        self, collection_name: str, source: str, n_results: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        소스 파일 기반 검색

        Args:
            collection_name: 컬렉션 이름
            source: 소스 파일명
            n_results: 반환할 결과 수

        Returns:
            검색 결과 리스트
        """
        return self.search_by_metadata(
            collection_name, where={"source": source}, n_results=n_results
        )

    def search_by_type(
        self, collection_name: str, chunk_type: str, n_results: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        청크 타입 기반 검색

        Args:
            collection_name: 컬렉션 이름
            chunk_type: 청크 타입 (text, table, heading 등)
            n_results: 반환할 결과 수

        Returns:
            검색 결과 리스트
        """
        return self.search_by_metadata(
            collection_name, where={"chunk_type": chunk_type}, n_results=n_results
        )

    def hybrid_search(
        self,
        query: str,
        collection_name: str,
        n_results: int = 5,
        metadata_filter: Dict[str, Any] = None,
        min_similarity: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """
        하이브리드 검색 (벡터 + 메타데이터)

        Args:
            query: 검색 쿼리
            collection_name: 컬렉션 이름
            n_results: 반환할 결과 수
            metadata_filter: 메타데이터 필터
            min_similarity: 최소 유사도 임계값

        Returns:
            검색 결과 리스트
        """
        results = self.search_similar(
            query=query,
            collection_name=collection_name,
            n_results=n_results,
            where=metadata_filter,
        )

        # 유사도 필터링
        if min_similarity > 0:
            results = [r for r in results if r["similarity"] >= min_similarity]

        return results


# 편의 함수들
def search_similar(
    query: str, collection_name: str, n_results: int = 5, where: Dict[str, Any] = None
) -> List[Dict[str, Any]]:
    """유사도 검색 편의 함수"""
    searcher = ChromaDBSearcher()
    return searcher.search_similar(query, collection_name, n_results, where)


def search_by_metadata(
    collection_name: str, where: Dict[str, Any], n_results: Optional[int] = None
) -> List[Dict[str, Any]]:
    """메타데이터 검색 편의 함수"""
    searcher = ChromaDBSearcher()
    return searcher.search_by_metadata(collection_name, where, n_results)
