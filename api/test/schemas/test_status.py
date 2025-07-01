# api/test/schemas/test_progress.py
from enum import Enum

from pydantic import BaseModel


class TestStatus(str, Enum):
    """테스트 생성 단계"""

    INITIALIZING = "INITIALIZING"  # 초기화 (0-10%)
    PARSING_DOCUMENTS = "PARSING_DOCUMENTS"  # 문서 분석 (10-30%)
    DESIGNING_TEST = "DESIGNING_TEST"  # 테스트 설계 (30-50%)
    GENERATING_QUESTIONS = "GENERATING_QUESTIONS"  # 문제 생성 (50-90%)
    FINALIZING = "FINALIZING"  # 최종화 (90-100%)


class TestStatusResponse(BaseModel):
    """테스트 생성 상태 응답"""

    documentId: int
    status: TestStatus
