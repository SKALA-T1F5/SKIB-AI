# ai/api/websocket/schemas/task_progress.py
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TaskStatus(str, Enum):
    """공통 작업 상태 - SpringBoot와 동일"""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TaskProgress(BaseModel):
    """Redis 저장용 진행률 모델"""

    model_config = ConfigDict(use_enum_values=True)

    task_id: str
    status: TaskStatus
    progress: float = Field(ge=0.0, le=100.0, description="진행률 (0-100)")
    message: Optional[str] = Field(default=None, description="상태 메시지")
    created_at: datetime
    updated_at: datetime


class ProgressUpdateRequest(BaseModel):
    """SpringBoot 전송용 진행률 업데이트"""

    model_config = ConfigDict(use_enum_values=True)

    status: TaskStatus = Field(..., description="작업 상태")
    progress: float = Field(..., ge=0.0, le=100.0, description="진행률 (0-100)")
    message: Optional[str] = Field(default=None, description="상태 메시지")
    timestamp: datetime = Field(default_factory=datetime.now, description="타임스탬프")


class ProgressResponse(BaseModel):
    """진행률 조회 응답"""

    model_config = ConfigDict(use_enum_values=True)

    status: TaskStatus
    progress: float
    message: Optional[str] = None
    updated_at: datetime
