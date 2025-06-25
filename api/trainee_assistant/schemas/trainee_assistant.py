from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class QuestionData(BaseModel):
    _id: Dict[str, str] = Field(..., description="MongoDB ObjectId")
    type: str = Field(..., description="문제 유형 (SUBJECTIVE, OBJECTIVE)")
    difficultyLevel: str = Field(..., description="난이도")
    question: str = Field(..., description="문제 내용")
    answer: str = Field(..., description="정답")
    explanation: str = Field(..., description="해설")
    documentId: str = Field(..., description="문서 ID")
    tags: List[str] = Field(default=[], description="태그 목록")

class ChatRequest(BaseModel):
    testId: str = Field(..., description="테스트 ID")
    question: Optional[QuestionData] = Field(None, description="문제 정보")

class ChatMessageRequest(BaseModel):
    session_id: str = Field(..., description="세션 ID")
    message: str = Field(..., description="사용자 메시지")
    question_context: Optional[ChatRequest] = Field(None, description="문제 컨텍스트")

# 🆕 새로운 워크플로우 응답 스키마
class WorkflowInfoResponse(BaseModel):
    search_executed: bool = Field(..., description="검색 실행 여부")
    search_query: Optional[str] = Field(None, description="검색 쿼리")
    search_result: Optional[Dict[str, Any]] = Field(None, description="검색 결과 정보")
    next_action: Optional[str] = Field(None, description="다음 액션 (use_vector_search/use_web_search)")
    results_count: Optional[int] = Field(None, description="검색 결과 개수")

# 🆕 강화된 채팅 응답 스키마
class EnhancedChatMessageResponse(BaseModel):
    response: str = Field(..., description="AI 응답")
    workflow_info: WorkflowInfoResponse = Field(..., description="워크플로우 정보")
    session_info: Dict[str, Any] = Field(..., description="세션 정보")
    timestamp: datetime = Field(default_factory=datetime.now, description="응답 시간")

# 🔄 기존 응답 스키마 (하위 호환성을 위해 유지)
class ChatMessageResponse(BaseModel):
    response: str = Field(..., description="AI 응답")
    session_info: Dict[str, Any] = Field(..., description="세션 정보")
    timestamp: datetime = Field(default_factory=datetime.now, description="응답 시간")

class SessionInfo(BaseModel):
    session_id: str = Field(..., description="세션 ID")
    total_messages: int = Field(..., description="총 메시지 수")
    question_context: Dict[str, Any] = Field(..., description="문제 컨텍스트")
    last_message_time: Optional[str] = Field(None, description="마지막 메시지 시간")

# 🆕 지식 문서 추가 요청 스키마
class AddKnowledgeRequest(BaseModel):
    session_id: str = Field(..., description="세션 ID")
    documents: List[str] = Field(..., description="추가할 문서 목록")
    metadatas: Optional[List[Dict[str, Any]]] = Field(None, description="문서 메타데이터 목록")

class AddKnowledgeResponse(BaseModel):
    message: str = Field(..., description="결과 메시지")
    documents_added: int = Field(..., description="추가된 문서 수")
    session_id: str = Field(..., description="세션 ID")