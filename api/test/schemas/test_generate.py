from typing import List

from pydantic import BaseModel

from api.question.schemas.question import DifficultyLevel, QuestionsByDocumentConfig


class FinalTestConfig(BaseModel):
    name: str
    difficulty_level: DifficultyLevel
    limited_time: int
    pass_score: int
    retake: bool
    document_configs: List[QuestionsByDocumentConfig]  # 사용자가 수정했을 수 있음


class TestGenerationRequest(BaseModel):
    final_test_config: FinalTestConfig  # 사용자 수정된 최종 설정
    project_id: int
