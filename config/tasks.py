from typing import Any, Dict

from api.document.routers.document_summary import process_document_background
from config.celery_app import celery_app


@celery_app.task(name="process_document")
def process_document_task(
    task_id: str, file_path: str, documentId: int, project_id: int, filename: str
) -> Dict[str, Any]:
    """문서 처리 Celery Task - 타입 힌트 추가"""
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        result = loop.run_until_complete(
            process_document_background(
                task_id, file_path, documentId, project_id, filename
            )
        )
        return {"status": "completed", "result": result}
    except Exception as e:
        return {"status": "failed", "error": str(e)}
    finally:
        loop.close()
