# main.py (기존 코드 + 추가)
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 기존 라우터들
from api.document.routers.document_summary import router as document_summary_router
from api.document.routers.document_upload import router as document_router
from api.feedback.routers.trainer import router as document_grading_router
from api.grading.routers.subjective_grading import router as grading_router
from api.test.routers.test_generate import router as test_generate_router
from api.test.routers.test_plan import router as test_plan_router
from api.trainee_assistant.routers.trainee_assistant import (
    router as trainee_assistant_router,
)

# 백그라운드 워커
from services.middleware import LoggingMiddleware

os.environ["TOKENIZERS_PARALLELISM"] = "false"


# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     """앱 시작/종료시 실행되는 라이프사이클 관리"""
#     # 시작시: 백그라운드 재시도 워커 시작
#     retry_task = asyncio.create_task(start_retry_worker())

#     yield

#     # 종료시: 백그라운드 워커 중지
#     stop_retry_worker()
#     retry_task.cancel()
#     try:
#         await retry_task
#     except asyncio.CancelledError:
#         pass


app = FastAPI(
    title="SKIB-AI FastAPI Server",
    version="1.0.0",
    # lifespan=lifespan,  # 라이프사이클 관리 추가
)

# CORS 먼저 등록!
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://skib-frontend.skala25a.project.skala-ai.com"
    ],  # 실제 서비스 도메인만 명시하는 게 안전합니다
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 미들웨어 및 라우터 등록
app.add_middleware(LoggingMiddleware)

# 기존 라우터들
app.include_router(test_generate_router)  # 업데이트된 비동기 테스트 생성 포함
app.include_router(grading_router)
app.include_router(document_router)
app.include_router(document_summary_router)
app.include_router(test_plan_router)
app.include_router(document_grading_router)
app.include_router(trainee_assistant_router)
