"""
ChromaDB 파이프라인 - 문서 처리부터 업로드까지의 통합 워크플로우
"""

import logging
from typing import Any, Dict, List

from .client import get_client
from .search import ChromaDBSearcher
from .upload import ChromaDBUploader, DuplicateAction
from .utils import get_collection_info, list_collections

logger = logging.getLogger(__name__)


class ChromaDBPipeline:
    """ChromaDB 통합 파이프라인"""

    def __init__(
        self, 
        embedding_model: str = "BAAI/bge-base-en",
        duplicate_action: DuplicateAction = DuplicateAction.SKIP
    ):
        """
        파이프라인 초기화

        Args:
            embedding_model: 임베딩 모델명
            duplicate_action: 중복 발견 시 처리 방식
        """
        self.client = get_client()
        self.uploader = ChromaDBUploader(embedding_model, duplicate_action)
        self.searcher = ChromaDBSearcher(embedding_model)
        self.duplicate_action = duplicate_action
        logger.info(f"🚀 ChromaDB 파이프라인 초기화 완료")
        logger.info(f"🔄 중복 처리 방식: {duplicate_action.value}")

    def process_and_upload_document(
        self,
        document_blocks: List[Dict[str, Any]],
        collection_name: str,
        source_file: str,
        recreate_collection: bool = False,
        duplicate_action: DuplicateAction = None,
    ) -> Dict[str, Any]:
        """
        문서 블록 처리 및 업로드 (중복 방지 기능 포함)

        Args:
            document_blocks: 문서 블록 리스트
            collection_name: 컬렉션 이름
            source_file: 소스 파일명
            recreate_collection: 컬렉션 재생성 여부
            duplicate_action: 중복 처리 방식 (없으면 기본값 사용)

        Returns:
            처리 결과 딕셔너리
        """
        try:
            logger.info(f"📄 문서 처리 시작: {source_file} → {collection_name}")

            # 컬렉션 재생성 처리
            if recreate_collection:
                from .utils import create_or_get_collection

                create_or_get_collection(collection_name, recreate=True)

            # 문서 블록 업로드 (중복 방지 적용)
            action = duplicate_action or self.duplicate_action
            uploaded_count = self.uploader.upload_document_blocks(
                document_blocks, collection_name, source_file, duplicate_action=action
            )

            # 결과 정보 수집
            collection_info = get_collection_info(collection_name)

            result = {
                "status": "success",
                "collection_name": collection_name,
                "source_file": source_file,
                "uploaded_count": uploaded_count,
                "total_blocks": len(document_blocks),
                "collection_total": collection_info.get("count", 0),
                "upload_success_rate": (
                    uploaded_count / len(document_blocks) if document_blocks else 0
                ),
            }

            logger.info(
                f"✅ 문서 업로드 완료: {uploaded_count}/{len(document_blocks)}개"
            )
            return result

        except Exception as e:
            logger.error(f"❌ 문서 처리 실패: {e}")
            return {
                "status": "error",
                "error": str(e),
                "uploaded_count": 0,
                "total_blocks": len(document_blocks),
            }

    def search_and_analyze(
        self,
        query: str,
        collection_name: str,
        n_results: int = 5,
        metadata_filter: Dict[str, Any] = None,
        include_analysis: bool = True,
    ) -> Dict[str, Any]:
        """
        검색 및 결과 분석

        Args:
            query: 검색 쿼리
            collection_name: 컬렉션 이름
            n_results: 반환할 결과 수
            metadata_filter: 메타데이터 필터
            include_analysis: 분석 정보 포함 여부

        Returns:
            검색 결과 및 분석 정보
        """
        try:
            logger.info(f"🔍 검색 시작: '{query}' in {collection_name}")

            # 벡터 검색 실행
            results = self.searcher.search_similar(
                query=query,
                collection_name=collection_name,
                n_results=n_results,
                where=metadata_filter,
            )

            response = {
                "query": query,
                "collection_name": collection_name,
                "results": results,
                "result_count": len(results),
            }

            # 분석 정보 추가
            if include_analysis and results:
                analysis = {
                    "avg_similarity": sum(r["similarity"] for r in results)
                    / len(results),
                    "max_similarity": max(r["similarity"] for r in results),
                    "min_similarity": min(r["similarity"] for r in results),
                    "source_distribution": {},
                    "type_distribution": {},
                }

                # 소스 및 타입 분포 계산
                for result in results:
                    metadata = result.get("metadata", {})
                    source = metadata.get("source", "unknown")
                    chunk_type = metadata.get("chunk_type", "unknown")

                    analysis["source_distribution"][source] = (
                        analysis["source_distribution"].get(source, 0) + 1
                    )
                    analysis["type_distribution"][chunk_type] = (
                        analysis["type_distribution"].get(chunk_type, 0) + 1
                    )

                response["analysis"] = analysis

            logger.info(f"✅ 검색 완료: {len(results)}개 결과")
            return response

        except Exception as e:
            logger.error(f"❌ 검색 실패: {e}")
            return {
                "query": query,
                "collection_name": collection_name,
                "results": [],
                "result_count": 0,
                "error": str(e),
            }

    def bulk_process_documents(
        self, documents: List[Dict[str, Any]], base_collection_name: str = None
    ) -> List[Dict[str, Any]]:
        """
        여러 문서 일괄 처리

        Args:
            documents: 문서 정보 리스트
                      [{"blocks": [...], "source_file": "...", "collection_name": "..."}, ...]
            base_collection_name: 기본 컬렉션 이름 (개별 컬렉션명이 없을 때 사용)

        Returns:
            처리 결과 리스트
        """
        results = []

        for i, doc in enumerate(documents):
            try:
                blocks = doc.get("blocks", [])
                source_file = doc.get("source_file", f"document_{i}")
                collection_name = doc.get(
                    "collection_name", base_collection_name or f"collection_{i}"
                )

                result = self.process_and_upload_document(
                    blocks, collection_name, source_file
                )

                results.append(result)

            except Exception as e:
                logger.error(f"❌ 문서 {i} 처리 실패: {e}")
                results.append(
                    {
                        "status": "error",
                        "error": str(e),
                        "source_file": doc.get("source_file", f"document_{i}"),
                    }
                )

        # 전체 통계
        total_uploaded = sum(r.get("uploaded_count", 0) for r in results)
        total_blocks = sum(r.get("total_blocks", 0) for r in results)
        success_count = sum(1 for r in results if r.get("status") == "success")

        logger.info(
            f"📊 일괄 처리 완료: {success_count}/{len(documents)}개 문서, {total_uploaded}/{total_blocks}개 블록"
        )

        return results

    def get_pipeline_status(self) -> Dict[str, Any]:
        """파이프라인 상태 정보"""
        try:
            from .utils import get_collection_stats

            stats = get_collection_stats()
            client_info = self.client.get_info()

            status = {
                "client_status": (
                    "connected" if self.client.test_connection() else "disconnected"
                ),
                "client_info": client_info,
                "database_stats": stats,
                "collections": list_collections(),
            }

            return status

        except Exception as e:
            logger.error(f"❌ 상태 조회 실패: {e}")
            return {"error": str(e)}


# 편의 함수들
def quick_upload(
    document_blocks: List[Dict[str, Any]],
    collection_name: str,
    source_file: str = "document",
) -> Dict[str, Any]:
    """빠른 문서 업로드"""
    pipeline = ChromaDBPipeline()
    return pipeline.process_and_upload_document(
        document_blocks, collection_name, source_file
    )


def quick_search(
    query: str, collection_name: str, n_results: int = 5
) -> List[Dict[str, Any]]:
    """빠른 검색"""
    pipeline = ChromaDBPipeline()
    result = pipeline.search_and_analyze(
        query, collection_name, n_results, include_analysis=False
    )
    return result.get("results", [])
