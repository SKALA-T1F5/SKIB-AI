"""
BaseState - Agent 및 Pipeline에서 사용하는 기본 상태 클래스

State는 Agent/Pipeline 간 데이터 공유 및 맥락 유지를 담당합니다.
TypedDict를 기반으로 하여 LangGraph와 호환됩니다.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, TypedDict


class StateStatus(str, Enum):
    """상태 진행 상황"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class BaseState(TypedDict, total=False):
    """
    모든 Agent와 Pipeline에서 공유하는 기본 상태 스키마

    LangGraph 호환성을 위해 TypedDict 사용
    total=False로 설정하여 모든 필드를 선택적으로 만듦
    """

    # 기본 메타데이터
    session_id: str  # 세션 고유 ID
    request_id: str  # 요청 고유 ID
    user_id: Optional[str]  # 사용자 ID
    created_at: datetime  # 생성 시간
    updated_at: datetime  # 최종 업데이트 시간

    # 진행 상황 추적
    status: StateStatus  # 현재 상태
    current_agent: Optional[str]  # 현재 실행 중인 Agent
    progress: float  # 진행률 (0.0-1.0)

    # 에러 및 로깅
    errors: List[Dict[str, Any]]  # 발생한 에러들
    warnings: List[str]  # 경고 메시지들
    logs: List[Dict[str, Any]]  # 실행 로그들

    # 메시지 및 대화
    messages: List[Dict[str, Any]]  # LangGraph 메시지 체인
    context: Dict[str, Any]  # 추가 컨텍스트 정보

    # 결과 및 출력
    output: Optional[Dict[str, Any]]  # 최종 출력 결과
    intermediate_results: Dict[str, Any]  # 중간 결과들


class QuestionGeneratorState(BaseState, total=False):
    """문제 생성 Agent 전용 상태"""

    # 생성 요구사항
    num_objective: int
    num_subjective: int
    difficulty_level: str
    target_topics: Optional[List[str]]

    # 소스 정보
    source_documents: List[Dict[str, Any]]
    source_chunks: List[Dict[str, Any]]

    # 생성된 문제들
    generated_questions: List[Dict[str, Any]]
    question_metadata: Dict[str, Any]

    # 생성 설정
    generation_strategy: str
    quality_threshold: float


class TestDesignerState(BaseState, total=False):
    """테스트 설계 Agent 전용 상태"""

    # 테스트 요구사항
    test_requirements: Dict[str, Any]
    target_audience: str
    time_limit: Optional[int]
    passing_score: Optional[float]

    # 설계 결과
    test_structure: Optional[Dict[str, Any]]
    question_distribution: Optional[Dict[str, Any]]
    estimated_duration: Optional[int]

    # 설계 전략
    design_strategy: str
    balance_criteria: Dict[str, Any]


class GraderState(BaseState, total=False):
    """채점 Agent 전용 상태"""

    # 채점 대상
    test_id: str
    student_answers: List[Dict[str, Any]]
    grading_criteria: List[Dict[str, Any]]

    # 채점 결과
    scores: List[Dict[str, Any]]
    feedback: List[Dict[str, Any]]
    total_score: Optional[float]
    grade: Optional[str]

    # 채점 설정
    grading_strategy: str
    consistency_check: bool


class AssistantState(BaseState, total=False):
    """Assistant Agent 전용 상태"""

    # 대화 컨텍스트
    conversation_history: List[Dict[str, Any]]
    current_query: str
    query_intent: Optional[str]

    # 검색 및 참조
    retrieved_documents: List[Dict[str, Any]]
    web_search_results: Optional[List[Dict[str, Any]]]
    reference_sources: List[str]

    # 응답 생성
    response: Optional[str]
    response_confidence: Optional[float]
    response_sources: List[str]

    # Assistant 설정
    response_style: str
    max_context_length: int


def create_base_state(
    session_id: str, request_id: str, user_id: Optional[str] = None
) -> BaseState:
    """BaseState 인스턴스를 생성하는 팩토리 함수"""

    now = datetime.now()

    return BaseState(
        session_id=session_id,
        request_id=request_id,
        user_id=user_id,
        created_at=now,
        updated_at=now,
        status=StateStatus.PENDING,
        progress=0.0,
        errors=[],
        warnings=[],
        logs=[],
        messages=[],
        context={},
        intermediate_results={},
    )


def update_state_progress(
    state: BaseState,
    progress: float,
    current_agent: Optional[str] = None,
    status: Optional[StateStatus] = None,
) -> BaseState:
    """State의 진행 상황을 업데이트하는 헬퍼 함수"""

    state["updated_at"] = datetime.now()
    state["progress"] = max(0.0, min(1.0, progress))

    if current_agent:
        state["current_agent"] = current_agent

    if status:
        state["status"] = status

    return state


def add_state_log(
    state: BaseState,
    level: str,
    message: str,
    agent: Optional[str] = None,
    extra_data: Optional[Dict[str, Any]] = None,
) -> BaseState:
    """State에 로그를 추가하는 헬퍼 함수"""

    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "level": level,
        "message": message,
        "agent": agent or state.get("current_agent"),
        "data": extra_data or {},
    }

    if "logs" not in state:
        state["logs"] = []

    state["logs"].append(log_entry)
    return state


def add_state_error(
    state: BaseState,
    error_type: str,
    error_message: str,
    agent: Optional[str] = None,
    traceback: Optional[str] = None,
) -> BaseState:
    """State에 에러를 추가하는 헬퍼 함수"""

    error_entry = {
        "timestamp": datetime.now().isoformat(),
        "type": error_type,
        "message": error_message,
        "agent": agent or state.get("current_agent"),
        "traceback": traceback,
    }

    if "errors" not in state:
        state["errors"] = []

    state["errors"].append(error_entry)
    state["status"] = StateStatus.FAILED

    return state
