"""
ChromaDB 문서 업로드 및 임베딩 생성
"""

from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
import logging

from .client import get_client
from .utils import create_or_get_collection

logger = logging.getLogger(__name__)


class ChromaDBUploader:
    """ChromaDB 업로드 관리 클래스"""
    
    def __init__(self, embedding_model: str = "BAAI/bge-base-en"):
        """
        업로더 초기화
        
        Args:
            embedding_model: 임베딩 모델명
        """
        self.client = get_client()
        self.embedding_model = SentenceTransformer(embedding_model)
        logger.info(f"🧮 임베딩 모델 로드: {embedding_model}")
    
    def upload_chunk(
        self,
        content: str,
        collection_name: str,
        metadata: Dict[str, Any] = None,
        chunk_id: str = None
    ) -> bool:
        """
        단일 청크 업로드
        
        Args:
            content: 텍스트 내용
            collection_name: 컬렉션 이름
            metadata: 메타데이터
            chunk_id: 청크 ID (없으면 자동 생성)
            
        Returns:
            업로드 성공 여부
        """
        try:
            collection = create_or_get_collection(collection_name, self.client.get_client())
            
            if not content or not isinstance(content, str):
                logger.warning(f"⚠️ 유효하지 않은 콘텐츠")
                return False
            
            # 메타데이터 정리 (ChromaDB는 특정 타입만 지원)
            clean_metadata = self._clean_metadata(metadata or {})
            clean_metadata.update({
                "project": collection_name,
                "upload_method": "chromadb_uploader"
            })
            
            # 청크 ID 생성
            if not chunk_id:
                existing_count = collection.count()
                chunk_id = f"{collection_name}_{existing_count}"
            
            # 임베딩 생성
            embedding = self.embedding_model.encode(content).tolist()
            
            # ChromaDB에 추가
            collection.add(
                documents=[content],
                metadatas=[clean_metadata],
                embeddings=[embedding],
                ids=[chunk_id]
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
        batch_size: int = 50
    ) -> Dict[str, int]:
        """
        배치 업로드
        
        Args:
            chunks: 청크 데이터 리스트
            collection_name: 컬렉션 이름
            batch_size: 배치 크기
            
        Returns:
            업로드 통계 {"successful": int, "failed": int, "total": int}
        """
        try:
            collection = create_or_get_collection(collection_name, self.client.get_client())
            
            successful = 0
            failed = 0
            
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i:i + batch_size]
                
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
                        metadata.update({
                            "chunk_type": chunk.get("type", "text"),
                            "source": chunk.get("source", "unknown"),
                            "project": collection_name
                        })
                        
                        # 임베딩 생성
                        embedding = self.embedding_model.encode(content).tolist()
                        
                        documents.append(content)
                        metadatas.append(metadata)
                        embeddings.append(embedding)
                        ids.append(chunk.get("id", f"{collection_name}_{i + j}"))
                    
                    if documents:
                        collection.add(
                            documents=documents,
                            metadatas=metadatas,
                            embeddings=embeddings,
                            ids=ids
                        )
                        successful += len(documents)
                        logger.info(f"✅ 배치 {i//batch_size + 1} 업로드 완료: {len(documents)}개")
                
                except Exception as e:
                    logger.error(f"❌ 배치 {i//batch_size + 1} 업로드 실패: {e}")
                    failed += len(batch)
            
            result = {
                "successful": successful,
                "failed": failed,
                "total": len(chunks)
            }
            
            logger.info(f"📊 배치 업로드 완료: {successful}/{len(chunks)}개 성공")
            return result
            
        except Exception as e:
            logger.error(f"❌ 배치 업로드 실패: {e}")
            return {"successful": 0, "failed": len(chunks), "total": len(chunks)}
    
    def upload_document_blocks(
        self,
        blocks: List[Dict[str, Any]],
        collection_name: str,
        source_file: str = "document"
    ) -> int:
        """
        문서 블록들을 업로드 (이미지 블록 포함)
        
        Args:
            blocks: 문서 블록 리스트
            collection_name: 컬렉션 이름
            source_file: 소스 파일명
            
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
                    "chunk_id": f"{collection_name}_{i}"
                }
            }
            chunks.append(chunk)
        
        result = self.batch_upload(chunks, collection_name)
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
    blocks: List[Dict[str, Any]],
    collection_name: str,
    source_file: str = "document"
) -> int:
    """문서 블록 업로드 편의 함수"""
    uploader = ChromaDBUploader()
    return uploader.upload_document_blocks(blocks, collection_name, source_file)


def upload_chunks(
    chunks: List[Dict[str, Any]],
    collection_name: str,
    batch_size: int = 50
) -> Dict[str, int]:
    """청크 배치 업로드 편의 함수"""
    uploader = ChromaDBUploader()
    return uploader.batch_upload(chunks, collection_name, batch_size)


def batch_upload(
    chunks: List[Dict[str, Any]],
    collection_name: str,
    batch_size: int = 50
) -> Dict[str, int]:
    """배치 업로드 편의 함수 (별칭)"""
    return upload_chunks(chunks, collection_name, batch_size)