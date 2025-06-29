# api/trainee_assistant/routers/trainee_assistant.py

from typing import List

from fastapi import APIRouter

from agents.trainee_assistant.initializer import (  # 경로는 실제 위치에 맞게 수정
    init_prompt_with_test_info,
)

router = APIRouter(prefix="/chat", tags=["Trainee Assistant"])


@router.post("/init")
async def initialize_test_context(test_questions: List[dict]):
    intro_msg = await init_prompt_with_test_info(test_questions)
    return {"context_summary": intro_msg}
