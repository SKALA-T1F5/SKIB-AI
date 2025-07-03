from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class TestGenerationStatus(str, Enum):
    """테스트 생성 세부 단계 상태"""

    TEST_GENERATION_STARTED = "TEST_GENERATION_STARTED"  # 테스트 생성 시작
    LOADING_TEST_PLAN = "LOADING_TEST_PLAN"  # 테스트 설계안 로드
    REFLECTING_TEST_PLAN = "REFLECTING_TEST_PLAN"  # 문제 유형/난이도/태그별로 슬롯 분배
    RETRIEVING_CONTEXTS = "RETRIEVING_CONTEXTS"  # 각 슬롯에 맞는 문맥/근거 검색
    PREPROCESSING_CONTEXTS = "PREPROCESSING_CONTEXTS"  # 문맥 요약, 필터링, 포맷팅
    GENERATING_QUESTIONS = "GENERATING_QUESTIONS"  # GPT 기반 문제 생성
    POSTPROCESSING_QUESTIONS = (
        "POSTPROCESSING_QUESTIONS"  # 잘린 문제 제거, 태그/형식 검증
    )
    FINALIZING_RESULTS = "FINALIZING_RESULTS"  # 테스트 세트로 저장
    COMPLETED = "COMPLETED"  # 문제 생성 전체 완료
    FAILED = "FAILED"  # 문제 생성 실패


class TestStatusResponse(BaseModel):
    """테스트 생성 상태 응답"""

    model_config = ConfigDict(use_enum_values=True)

    testId: int = Field(..., alias="testId", description="테스트 ID")
    status: TestGenerationStatus

    model_config = {"populate_by_name": True}
