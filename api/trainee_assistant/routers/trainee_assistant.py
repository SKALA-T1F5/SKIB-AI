# api/trainee_assistant/routers/trainee_assistant.py

from typing import List

from fastapi import APIRouter

from api.trainee_assistant.schemas.trainee_assistant import (
    InitializeTestRequest,
    QuestionPayload,
)
from db.redisDB.session_manager import (
    clear_user_session,
    load_test_questions,
    save_test_questions,
)
from src.pipelines.trainee_assistant.trainee_assistant import build_langgraph

router = APIRouter(prefix="/chat", tags=["Trainee Assistant"])
chat_graph = build_langgraph()


@router.post("/init")
async def initialize_test_context(payload: InitializeTestRequest):
    user_id = payload.userId
    test_questions = payload.testQuestions

    await save_test_questions(user_id, test_questions)
    return {"msg": "테스트 문항 초기화 완료"}


from api.trainee_assistant.schemas.trainee_assistant import Question


@router.post("/ask-graph")
async def ask_with_langgraph(payload: QuestionPayload):
    test_questions_raw = await load_test_questions(payload.userId)
    question_data = next(
            (q for q in test_questions_raw if q.id == payload.id), None
    )

    result = await chat_graph.ainvoke(
        {
            "user_id": payload.userId,
            "question": payload.question,
            "question_id": payload.id,
            "test_questions": test_questions_raw,
        }
    )
    return {"answer": result["answer"]}


@router.post("/session/reset")
async def reset_user_session(user_id: str):
    await clear_user_session(user_id)
    return {"msg": f"✅ 세션 초기화 완료 (user_id={user_id})"}
