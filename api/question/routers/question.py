# ai/api/question/routers/question_router.py
from typing import List

from fastapi import APIRouter

from api.question.schemas.question import QuestionResponse, QuestionsByDocumentConfig
from src.pipelines.question_generation import run_pipeline

router = APIRouter(prefix="/api", tags=["Question Generator"])


@router.post("/question", response_model=List[QuestionResponse])
def generate_questions(
    request: QuestionsByDocumentConfig,
):
    # 문제 생성 실행
    questions = run_pipeline(
        pdf_path=request.documentId,
        num_objective=request.configuredObjectiveCount,
        num_subjective=request.configuredSubjectiveCount,
    )

    return questions
