import os

from fastapi import FastAPI

from api.document.routers.document_summary import router as document_summary_router
from api.document.routers.document_upload import router as document_router
from api.grading.routers.subjective_grading import router as grading_router
from api.question.routers.question import router as question_router
from services.middleware import LoggingMiddleware  # 위 클래스 저장 파일 경로

os.environ["TOKENIZERS_PARALLELISM"] = "false"

app = FastAPI(title="SKIB-AI FastAPI Server", version="1.0.0")

# Include routers
app.add_middleware(LoggingMiddleware)
app.include_router(question_router)
app.include_router(grading_router)
app.include_router(document_router)
app.include_router(document_summary_router)
