# ai/api/question/routers/question_router.py
from fastapi import APIRouter, HTTPException
from datetime import datetime
from typing import List
import os
from api.question.schemas.question import QuestionResponse, QuestionConfig
from src.agents.question_generator.run_pipeline import run_pipeline

router = APIRouter(prefix="/api", tags=["Question Generator"])


@router.post("/question", response_model=List[QuestionResponse])
def generate_questions(
    request: QuestionConfig,
):
    # 문제 생성 실행
    questions = run_pipeline(
        pdf_path=request.documentId,
        num_objective=request.configuredObjectiveCount,
        num_subjective=request.configuredSubjectiveCount,
    )

    return questions