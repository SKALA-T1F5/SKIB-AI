import asyncio
import logging
import time
from typing import Dict

import httpx

from api.document.schemas.document_status import (
    DocumentProcessingStatus,
    StatusEnum,
    set_status,
)
from api.document.schemas.document_summary import (
    set_result,
)
from api.websocket.services.springboot_notifier import notify_document_progress
from config.settings import settings
from src.pipelines.document_processing.pipeline import DocumentProcessingPipeline

logger = logging.getLogger(__name__)


async def process_document_background(
    task_id: str, file_path: str, documentId: int, project_id: int, filename: str
):
    """
    문서 전처리 백그라운드 실행
    """
    try:
        logger.info(f"Starting background processing for documentId: {documentId}")

        pipeline = DocumentProcessingPipeline(
            config={
                "enable_vectordb": True,
                "timeout_seconds": 600,
                "max_retries": 3,
                "task_id": task_id,
            }
        )

        result = await pipeline.run(
            {
                "document_path": file_path,
                "documentId": documentId,
                "project_id": project_id,
                "filename": filename,
            }
        )

        if result.get("processing_status") == "completed":
            content_analysis = result.get("content_analysis", {})
            main_topics = content_analysis.get("main_topics", [])
            key_concepts = content_analysis.get("key_concepts", [])
            keywords = (main_topics + key_concepts)[:10]

            summary_data = {
                "summary": content_analysis.get("summary", ""),
                "keywords": keywords,
                "document_id": documentId,
                "name": result.get("filename", ""),
            }

            # 1. 결과 저장 # TODO REDIS 저장으로 바꿔야 함
            set_result(documentId, summary_data)
            logger.info(f"📝 Summary completed for documentId: {documentId}")

            # 2. SpringBoot에 알림 (3번 재시도 포함)
            success = await notify_springboot_completion(documentId, summary_data)

            if success:
                set_status(documentId, StatusEnum.DONE)
                # 3. 전송 성공 → DONE
                await notify_document_progress(
                    task_id=task_id,
                    document_id=documentId,
                    status=DocumentProcessingStatus.SUMMARY_COMPLETED,
                )
                logger.info(f"✅ 문서 처리 완료: {documentId}")
            else:
                # 4. 3번 재시도 모두 실패 → FAILED
                set_status(documentId, StatusEnum.FAILED)

                # 실패 알림
                await notify_document_progress(
                    task_id=task_id,
                    document_id=documentId,
                    status=DocumentProcessingStatus.FAILED,
                    error_code="SUMMARY_UPLOAD_FAILED",
                )

                logger.error(
                    f"❌ SpringBoot 전송 3번 재시도 모두 실패: documentId: {documentId}"
                )
        else:
            # Pipeline 자체 실패 → FAILED
            set_status(documentId, StatusEnum.FAILED)

            await notify_document_progress(
                task_id=task_id,
                document_id=documentId,
                status=DocumentProcessingStatus.FAILED,
                error_code="PROCESSING_FAILED",
            )
            logger.error(f"❌ Pipeline failed for documentId: {documentId}")

    except Exception as e:
        # 예외 발생 시 실패 상태
        set_status(documentId, StatusEnum.FAILED)

        await notify_document_progress(
            task_id=task_id,
            document_id=documentId,
            status=DocumentProcessingStatus.FAILED,
            error_code="PROCESSING_EXCEPTION",
        )

        logger.error(
            f"❌ Exception in background processing for documentId {documentId}: {str(e)}"
        )


async def notify_springboot_completion(
    documentId: int, summary_data: Dict, max_duration_minutes: int = 30
) -> bool:
    """SpringBoot에 처리 완료 알림 (200 OK까지 재시도, 최대 30분)"""
    url = f"{settings.backend_url}/api/document/summary/{documentId}"
    start_time = time.time()
    max_duration_seconds = max_duration_minutes * 60
    attempt = 0

    while True:
        attempt += 1
        try:
            logger.info(f"📡 SpringBoot 전송 시도 {attempt}: documentId={documentId}")
            logger.info(f"🌍 전송 대상 URL: {url}")
            logger.info(f"📡 전송 대상 데이터: {summary_data}")

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.put(
                    url,
                    json=summary_data,
                    headers={"Content-Type": "application/json"},
                )

            logger.info(f"📡 SpringBoot 응답 코드: {response.status_code}")
            logger.info(f"📡 SpringBoot 응답 내용: {response.text}")

            if response.status_code == 200:
                logger.info(
                    f"✅ SpringBoot 알림 성공: documentId={documentId} (시도 {attempt})"
                )
                return True
            else:
                logger.warning(
                    f"⚠️ SpringBoot 알림 실패 (시도 {attempt}): "
                    f"상태 코드 {response.status_code}, 응답 내용: {response.text}"
                )

        except Exception as e:
            logger.warning(f"⚠️ SpringBoot 알림 중 예외 발생 (시도 {attempt}): {str(e)}")

        # 최대 시간 초과 확인
        elapsed_time = time.time() - start_time
        if elapsed_time >= max_duration_seconds:
            logger.error(
                f"❌ SpringBoot 알림 시간 초과: documentId={documentId} "
                f"({attempt}번 시도, {elapsed_time:.1f}초 경과)"
            )
            return False

        # 재시도 대기 (지수 백오프, 최대 60초)
        wait_time = min(2 ** min(attempt - 1, 6), 60)  # 2, 4, 8, 16, 32, 60, 60, ...
        logger.info(f"⏳ {wait_time}초 후 재시도... (경과 시간: {elapsed_time:.1f}초)")
        await asyncio.sleep(wait_time)
