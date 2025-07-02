import asyncio
from typing import Any, Dict

from api.document.services.document_summary import process_document_background
from config.celery_app import celery_app


@celery_app.task(name="process_document", queue="preprocessing_queue")
def process_document_task(
    task_id: str, file_path: str, documentId: int, project_id: int, filename: str
) -> Dict[str, Any]:
    """문서 처리 Celery Task - 타입 힌트 추가"""
    try:
        result = asyncio.run(
            process_document_background(
                task_id, file_path, documentId, project_id, filename
            )
        )
        return {"status": "completed", "result": result}
    except Exception as e:
        return {"status": "failed", "error": str(e)}
