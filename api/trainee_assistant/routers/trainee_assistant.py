from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List
import uuid
from datetime import datetime

from api.trainee_assistant.schemas import (
    ChatMessageRequest, 
    ChatMessageResponse, 
    SessionInfo
)
# 📝 변경사항: pipeline import 경로는 동일하게 유지
from src.pipelines.trainee_assistant.pipeline import TraineeAssistantPipeline

router = APIRouter(prefix="/trainee-assistant", tags=["Trainee Assistant RAG"])

# 전역 파이프라인 인스턴스
pipeline = TraineeAssistantPipeline()

@router.post("/chat", response_model=ChatMessageResponse)
async def send_chat_message(request: ChatMessageRequest):
    """
    RAG 기반 채팅 메시지 전송
    🟢 [1] → 🔵 [2] → 🟡 [3A/3B] 파이프라인 실행
    """
    try:
        question_context = None
        if request.question_context:
            question_context = {
                "testId": request.question_context.testId,
                "question": request.question_context.question.dict() if request.question_context.question else None
            }
        
        result = await pipeline.process_chat_message(
            session_id=request.session_id,
            user_message=request.message,
            question_context=question_context
        )
        
        return ChatMessageResponse(
            response=result["response"],
            session_info=result["session_info"],
            timestamp=datetime.now()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG 채팅 처리 중 오류: {str(e)}")

@router.post("/knowledge/add")
async def add_knowledge_documents(
    session_id: str,
    documents: List[str],
    metadatas: List[Dict[str, Any]] = None
):
    """
    지식 베이스에 문서 추가
    """
    try:
        result = await pipeline.add_knowledge_documents(session_id, documents, metadatas)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"지식 문서 추가 중 오류: {str(e)}")

@router.get("/session/{session_id}", response_model=SessionInfo)
async def get_session_info(session_id: str):
    """
    세션 정보 조회
    """
    try:
        agent = pipeline.get_or_create_session(session_id)
        summary = agent.get_conversation_summary()
        
        return SessionInfo(
            session_id=session_id,
            total_messages=summary["total_messages"],
            question_context=summary["question_context"],
            last_message_time=summary["last_message_time"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"세션 정보 조회 중 오류가 발생했습니다: {str(e)}")

@router.delete("/session/{session_id}")
async def cleanup_session(session_id: str):
    """
    세션 정리
    """
    try:
        pipeline.cleanup_session(session_id)
        return {"message": f"세션 {session_id}이 정리되었습니다."}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"세션 정리 중 오류가 발생했습니다: {str(e)}")

@router.get("/sessions/count")
async def get_active_sessions_count():
    """
    활성 세션 수 조회
    """
    return {"active_sessions": pipeline.get_active_sessions_count()}

@router.post("/session/new")
async def create_new_session():
    """
    새 세션 생성
    """
    session_id = str(uuid.uuid4())
    agent = pipeline.get_or_create_session(session_id)
    
    return {
        "session_id": session_id,
        "created_at": datetime.now().isoformat(),
        "message": "새 세션이 생성되었습니다."
    }