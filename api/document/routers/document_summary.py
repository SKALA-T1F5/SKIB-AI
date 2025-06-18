from fastapi import HTTPException
from typing import Dict, Any
import logging

from api.document.schemas.document_summary import SummaryByDocumentResponse
from src.pipelines.document_processing.pipeline import DocumentProcessingPipeline
from fastapi import APIRouter

router = APIRouter()
logger = logging.getLogger(__name__)

# 간단한 결과 저장소 (기존 복잡한 PipelineManager 대신)
PIPELINE_RESULTS: Dict[int, Dict[str, Any]] = {}

@router.get("/api/document/summary/{document_id}", response_model=SummaryByDocumentResponse)
async def get_document_summary(document_id: int):
    """
    수정 포인트: 상태별 HTTP 응답 코드 정확히 처리
    """
    try:
        result = PIPELINE_RESULTS.get(document_id)
        print(f"Retrieving summary for document_id: {document_id}, result: {result}")
        
        # 1. 결과 없음 -> 404
        if not result:
            raise HTTPException(
                status_code=404, 
                detail="Document summary not found"
            )
        
        status = result.get("status", "unknown")
        
        # 2. 처리 중 -> 202 Accepted
        if status == "processing":
            raise HTTPException(
                status_code=202,
                detail="Document is still being processed"
            )
        
        # 3. 실패 -> 500 Error  
        if status == "failed":
            raise HTTPException(
                status_code=500,
                detail=f"Document processing failed: {result.get('error_message', 'Unknown error')}"
            )
        
        # 4. 완료 -> 200 OK + 데이터
        if status == "completed":
            return SummaryByDocumentResponse(
                summary=result.get("summary", ""),
                keywords=result.get("keywords", []),
                document_id=document_id
            )
        
        # 기타 상태 -> 500
        raise HTTPException(
            status_code=500,
            detail=f"Unknown processing status: {status}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Summary retrieval failed for document {document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Summary retrieval failed: {str(e)}")

# 백그라운드 함수 단순화
async def process_document_background(
    file_path: str,
    document_id: int,
    project_id: int,
    filename: str
):
    """백그라운드 처리 - 결과 저장 로직 단순화"""
    try:
        # 처리 중 상태 저장
        PIPELINE_RESULTS[document_id] = {
            "status": "processing",
            "document_id": document_id
        }
        
        logger.info(f"Starting background processing for document_id: {document_id}")
        
        # Pipeline 실행 (기존과 동일)
        pipeline = DocumentProcessingPipeline(config={
            "enable_vectordb": False, # 벡터 DB 사용 유무
            "timeout_seconds": 600,
            "max_retries": 3
        })
        
        result = await pipeline.run({
            "document_path": file_path,
            "document_id": document_id,
            "project_id": project_id,
            "filename": filename,
        })
        
        # 결과를 SpringBoot 형식으로 변환하여 저장
        if result.get("processing_status") == "completed":
            content_analysis = result.get("content_analysis", {})
            
            # SpringBoot SummaryDto 형식으로 변환
            main_topics = content_analysis.get("main_topics", [])
            key_concepts = content_analysis.get("key_concepts", [])
            keywords = (main_topics + key_concepts)[:10]  # 상위 10개만
            
            # 최종 결과 저장 (SpringBoot가 GET으로 가져갈 형식)
            PIPELINE_RESULTS[document_id] = {
                "status": "completed",
                "summary": content_analysis.get("summary", ""),
                "keywords": keywords,
                "document_id": document_id,
                "completed_at": result.get("completed_at")
            }
            
            logger.info(f"✅ Background processing completed for document_id: {document_id}")
        else:
            # 실패 처리
            PIPELINE_RESULTS[document_id] = {
                "status": "failed",
                "error_message": result.get("error_message", "Unknown error"),
                "document_id": document_id
            }
            logger.error(f"❌ Background processing failed for document_id: {document_id}")
        
    except Exception as e:
        # 예외 발생 시 실패 상태 저장
        PIPELINE_RESULTS[document_id] = {
            "status": "failed",
            "error_message": str(e),
            "document_id": document_id
        }
        print(f"❌ Background processing exception for document_id: {str(e)}")
        logger.error(f"Background processing exception for document_id {document_id}: {str(e)}")
