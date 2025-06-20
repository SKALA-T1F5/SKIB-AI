from typing import TypedDict


class BasePipelineState(TypedDict, total=False):
    """모든 Pipeline이 공유하는 기본 상태"""

    # 공통 식별자
    pipeline_id: str
    session_id: str

    # 진행 상황 추적
    current_step: str
    processing_status: str  # "pending", "running", "completed", "failed"
    progress_percentage: float

    # 에러 관리
    error_message: str
    retry_count: int

    # 메타데이터
    started_at: str
    completed_at: str
    total_steps: int
