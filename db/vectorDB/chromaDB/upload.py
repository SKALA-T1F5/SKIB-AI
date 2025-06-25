"""
ChromaDB 문서 업로드 및 임베딩 생성
"""

import hashlib
import logging
from enum import Enum
from typing import Any, Dict, List, Optional

from sentence_transformers import SentenceTransformer

from .client import get_client
from .utils import create_or_get_collection

logger = logging.getLogger(__name__)


class DuplicateAction(Enum):
    """중복 발견 시 처리 방식"""
    SKIP = "skip"          # 중복 시 스킵
    OVERWRITE = "overwrite"  # 중복 시 덮어쓰기
    ERROR = "error"        # 중복 시 에러 발생


def generate_content_hash(content: str, metadata: Optional[Dict] = None) -> str:
    """
    문서 내용 기반 고유 해시 ID 생성
    
    Args:
        content: 문서 내용
        metadata: 메타데이터 (파일명, 크기 등)
    
    Returns:
        str: 고유 해시 ID
    """
    # 내용 기반 해시
    content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]
    
    # 메타데이터 추가 정보 (있는 경우)
    if metadata:
        # 파일명, 페이지, 블록 타입 등으로 세분화
        extra_info = f"{metadata.get('source_file', '')}"
        extra_info += f"_p{metadata.get('page', 0)}"
        extra_info += f"_{metadata.get('element_type', 'text')}"
        extra_info += f"_{metadata.get('element_index', 0)}"
        
        extra_hash = hashlib.sha256(extra_info.encode('utf-8')).hexdigest()[:8]
        return f"{content_hash}_{extra_hash}"
    
    return content_hash


def check_document_exists(collection, chunk_id: str) -> bool:
    """
    문서 존재 여부 확인
    
    Args:
        collection: ChromaDB 컬렉션
        chunk_id: 확인할 문서 ID
    
    Returns:
        bool: 존재 여부
    """
    try:
        result = collection.get(ids=[chunk_id])
        return len(result.get('ids', [])) > 0
    except Exception as e:
        logger.warning(f"문서 존재 여부 확인 실패: {e}")
        return False


class ChromaDBUploader:
    """ChromaDB 업로드 관리 클래스"""

    def __init__(
        self, 
        embedding_model: str = "BAAI/bge-base-en",
        duplicate_action: DuplicateAction = DuplicateAction.SKIP
    ):
        """
        업로더 초기화

        Args:
            embedding_model: 임베딩 모델명
            duplicate_action: 중복 발견 시 처리 방식
        """
        self.client = get_client()
        self.embedding_model = SentenceTransformer(embedding_model)
        self.duplicate_action = duplicate_action
        logger.info(f"🧮 임베딩 모델 로드: {embedding_model}")
        logger.info(f"🔄 중복 처리 방식: {duplicate_action.value}")

    def upload_chunk(
        self,
        content: str,
        collection_name: str,
        metadata: Dict[str, Any] = None,
        chunk_id: str = None,
        duplicate_action: Optional[DuplicateAction] = None,
    ) -> bool:
        """
        단일 청크 업로드 (중복 방지 기능 포함)

        Args:
            content: 텍스트 내용
            collection_name: 컬렉션 이름
            metadata: 메타데이터
            chunk_id: 청크 ID (없으면 해시 기반 자동 생성)
            duplicate_action: 중복 처리 방식 (없으면 기본값 사용)

        Returns:
            업로드 성공 여부
        """
        try:
            collection = create_or_get_collection(
                collection_name, self.client.get_client()
            )

            if not content or not isinstance(content, str):
                logger.warning(f"⚠️ 유효하지 않은 콘텐츠")
                return False

            # 메타데이터 정리 (ChromaDB는 특정 타입만 지원)
            clean_metadata = self._clean_metadata(metadata or {})
            clean_metadata.update(
                {"project": collection_name, "upload_method": "chromadb_uploader"}
            )

            # 청크 ID 생성 (해시 기반)
            if not chunk_id:
                chunk_id = f"{collection_name}_{generate_content_hash(content, metadata)}"

            # 중복 검사 및 처리
            action = duplicate_action or self.duplicate_action
            if check_document_exists(collection, chunk_id):
                if action == DuplicateAction.SKIP:
                    logger.info(f"⏭️ 중복 문서 스킵: {chunk_id}")
                    return True
                elif action == DuplicateAction.ERROR:
                    logger.error(f"❌ 중복 문서 발견: {chunk_id}")
                    raise ValueError(f"중복 문서가 이미 존재합니다: {chunk_id}")
                elif action == DuplicateAction.OVERWRITE:
                    logger.info(f"🔄 중복 문서 덮어쓰기: {chunk_id}")
                    # 기존 문서 삭제
                    try:
                        collection.delete(ids=[chunk_id])
                    except Exception as e:
                        logger.warning(f"기존 문서 삭제 실패: {e}")

            # 임베딩 생성
            embedding = self.embedding_model.encode(content).tolist()

            # ChromaDB에 추가
            collection.add(
                documents=[content],
                metadatas=[clean_metadata],
                embeddings=[embedding],
                ids=[chunk_id],
            )

            logger.debug(f"✅ 청크 업로드 성공: {chunk_id}")
            return True

        except Exception as e:
            logger.error(f"❌ 청크 업로드 실패: {e}")
            return False

    def batch_upload(
        self, 
        chunks: List[Dict[str, Any]], 
        collection_name: str, 
        batch_size: int = 50,
        duplicate_action: Optional[DuplicateAction] = None
    ) -> Dict[str, int]:
        """
        배치 업로드 (중복 방지 기능 포함)

        Args:
            chunks: 청크 데이터 리스트
            collection_name: 컬렉션 이름
            batch_size: 배치 크기
            duplicate_action: 중복 처리 방식 (없으면 기본값 사용)

        Returns:
            업로드 통계 {"successful": int, "failed": int, "total": int, "skipped": int, "overwritten": int}
        """
        try:
            collection = create_or_get_collection(
                collection_name, self.client.get_client()
            )

            successful = 0
            failed = 0
            skipped = 0
            overwritten = 0
            action = duplicate_action or self.duplicate_action

            for i in range(0, len(chunks), batch_size):
                batch = chunks[i : i + batch_size]

                try:
                    documents = []
                    metadatas = []
                    embeddings = []
                    ids = []

                    for j, chunk in enumerate(batch):
                        content = chunk.get("content", "")
                        if not content or not isinstance(content, str):
                            failed += 1
                            continue

                        # 메타데이터 처리
                        metadata = self._clean_metadata(chunk.get("metadata", {}))
                        metadata.update(
                            {
                                "chunk_type": chunk.get("type", "text"),
                                "source": chunk.get("source", "unknown"),
                                "project": collection_name,
                            }
                        )

                        # 해시 기반 ID 생성
                        chunk_id = chunk.get("id")
                        if not chunk_id:
                            chunk_id = f"{collection_name}_{generate_content_hash(content, metadata)}"

                        # 중복 검사 및 처리
                        if check_document_exists(collection, chunk_id):
                            if action == DuplicateAction.SKIP:
                                skipped += 1
                                logger.debug(f"⏭️ 중복 문서 스킵: {chunk_id}")
                                continue
                            elif action == DuplicateAction.ERROR:
                                failed += 1
                                logger.error(f"❌ 중복 문서 발견: {chunk_id}")
                                continue
                            elif action == DuplicateAction.OVERWRITE:
                                overwritten += 1
                                logger.debug(f"🔄 중복 문서 덮어쓰기: {chunk_id}")
                                # 기존 문서 삭제
                                try:
                                    collection.delete(ids=[chunk_id])
                                except Exception as e:
                                    logger.warning(f"기존 문서 삭제 실패: {e}")

                        # 임베딩 생성
                        embedding = self.embedding_model.encode(content).tolist()

                        documents.append(content)
                        metadatas.append(metadata)
                        embeddings.append(embedding)
                        ids.append(chunk_id)

                    if documents:
                        collection.add(
                            documents=documents,
                            metadatas=metadatas,
                            embeddings=embeddings,
                            ids=ids,
                        )
                        successful += len(documents)
                        logger.info(
                            f"✅ 배치 {i//batch_size + 1} 업로드 완료: {len(documents)}개"
                        )

                except Exception as e:
                    logger.error(f"❌ 배치 {i//batch_size + 1} 업로드 실패: {e}")
                    failed += len(batch)

            result = {
                "successful": successful, 
                "failed": failed, 
                "total": len(chunks),
                "skipped": skipped,
                "overwritten": overwritten
            }

            logger.info(f"📊 배치 업로드 완료: {successful}/{len(chunks)}개 성공, {skipped}개 스킵, {overwritten}개 덮어쓰기")
            return result

        except Exception as e:
            logger.error(f"❌ 배치 업로드 실패: {e}")
            return {
                "successful": 0, 
                "failed": len(chunks), 
                "total": len(chunks),
                "skipped": 0,
                "overwritten": 0
            }

    def upload_document_blocks(
        self,
        blocks: List[Dict[str, Any]],
        collection_name: str,
        source_file: str = "document",
        duplicate_action: Optional[DuplicateAction] = None,
    ) -> int:
        """
        문서 블록들을 업로드 (이미지 블록 포함, 중복 방지)

        Args:
            blocks: 문서 블록 리스트
            collection_name: 컬렉션 이름
            source_file: 소스 파일명
            duplicate_action: 중복 처리 방식

        Returns:
            업로드된 청크 수
        """
        chunks = []

        for i, block in enumerate(blocks):
            block_type = block.get("type", "text")

            # 이미지 블록 특별 처리
            if block_type == "image":
                content = self._process_image_block(block)
            else:
                content = str(block.get("content", ""))

            # 빈 콘텐츠 스킵
            if not content.strip():
                logger.warning(f"빈 콘텐츠 블록 스킵: {block_type} 블록 {i}")
                continue

            chunk = {
                "content": content,
                "type": block_type,
                "source": source_file,
                "id": f"{collection_name}_{i}",
                "metadata": {
                    **block.get("metadata", {}),
                    "block_index": i,
                    "chunk_id": f"{collection_name}_{i}",
                },
            }
            chunks.append(chunk)

        result = self.batch_upload(chunks, collection_name, duplicate_action=duplicate_action)
        return result["successful"]

    def _process_image_block(self, block: Dict[str, Any]) -> str:
        """
        이미지 블록을 텍스트로 변환하여 검색 가능하게 만듦

        Args:
            block: 이미지 블록 정보

        Returns:
            검색 가능한 텍스트 내용
        """
        try:
            metadata = block.get("metadata", {})

            # 이미지 정보를 텍스트로 변환
            image_info = []

            # 기본 정보
            if metadata.get("page"):
                image_info.append(f"페이지 {metadata['page']}의 이미지")

            # 이미지 크기 정보
            if metadata.get("width") and metadata.get("height"):
                image_info.append(f"크기: {metadata['width']}x{metadata['height']}")

            # 파일 경로에서 추가 정보 추출
            image_path = block.get("content", "")
            if isinstance(image_path, str) and image_path:
                import os

                filename = os.path.basename(image_path)
                image_info.append(f"파일명: {filename}")

                # 파일명에서 의미 추출
                if "table" in filename.lower():
                    image_info.append("표 형태의 이미지")
                elif "chart" in filename.lower():
                    image_info.append("차트 또는 그래프 이미지")
                elif "diagram" in filename.lower():
                    image_info.append("다이어그램 이미지")
                elif "screenshot" in filename.lower():
                    image_info.append("화면 캡처 이미지")
                else:
                    image_info.append("일반 이미지")

            # OCR 텍스트가 있다면 포함
            if metadata.get("ocr_text"):
                image_info.append(f"추출된 텍스트: {metadata['ocr_text']}")

            # 이미지 설명이 있다면 포함
            if metadata.get("description"):
                image_info.append(f"설명: {metadata['description']}")

            # 캡션이 있다면 포함
            if metadata.get("caption"):
                image_info.append(f"캡션: {metadata['caption']}")

            content = " | ".join(image_info) if image_info else "이미지 블록"

            logger.debug(f"이미지 블록 변환: {content[:100]}...")
            return content

        except Exception as e:
            logger.warning(f"이미지 블록 처리 실패: {e}")
            return f"이미지 블록 (처리 실패: {str(e)[:50]})"

    def _clean_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """메타데이터 정리 (ChromaDB 호환성)"""
        clean_metadata = {}

        for key, value in metadata.items():
            if isinstance(value, (str, int, float, bool)):
                clean_metadata[key] = value
            elif value is not None:
                clean_metadata[key] = str(value)

        return clean_metadata


# 편의 함수들
def upload_documents(
    blocks: List[Dict[str, Any]], collection_name: str, source_file: str = "document"
) -> int:
    """문서 블록 업로드 편의 함수"""
    from .collection_utils import get_safe_collection_name
    
    # Collection 이름 정규화
    normalized_collection_name = get_safe_collection_name(collection_name)
    
    uploader = ChromaDBUploader()
    return uploader.upload_document_blocks(blocks, normalized_collection_name, source_file)


def upload_chunks(
    chunks: List[Dict[str, Any]], collection_name: str, batch_size: int = 50
) -> Dict[str, int]:
    """청크 배치 업로드 편의 함수"""
    from .collection_utils import get_safe_collection_name
    
    # Collection 이름 정규화
    normalized_collection_name = get_safe_collection_name(collection_name)
    
    uploader = ChromaDBUploader()
    return uploader.batch_upload(chunks, normalized_collection_name, batch_size)


def batch_upload(
    chunks: List[Dict[str, Any]], collection_name: str, batch_size: int = 50
) -> Dict[str, int]:
    """배치 업로드 편의 함수 (별칭)"""
    return upload_chunks(chunks, collection_name, batch_size)
