from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from api.grading.schemas.subjective_grading import GradingCriterion


# Enum 정의
class QuestionType(str, Enum):
    objective = "OBJECTIVE"  # 객관식
    subjective = "SUBJECTIVE"  # 서술형


class DifficultyLevel(str, Enum):
    easy = "EASY"
    normal = "NORMAL"
    hard = "HARD"


class QuestionConfig(BaseModel):
    documentId: int
    configuredObjectiveCount: int
    configuredSubjectiveCount: int


# 공통 베이스 모델
class QuestionResponse(BaseModel):
    type: QuestionType = Field(..., description="문제 유형 (OBJECTIVE 또는 SUBJECTIVE)")
    difficulty_level: DifficultyLevel = Field(..., description="문제 난이도")
    question: str = Field(..., description="문제 본문 텍스트")
    options: Optional[List[str]] = Field(
        None, description="객관식 선택지 (type이 객관식인 경우)"
    )
    answer: str = Field(..., description="객관식 문제 정답, ")
    explanation: Optional[str] = Field(None, description="정답에 대한 해설")
    grading_criteria: Optional[List[GradingCriterion]] = Field(
        None, description="주관식 문제 채점 기준"
    )
    document_id: int = Field(..., description="문제가 속한 문서의 고유 ID")
    document_name: str = Field(..., description="문제가 속한 문서의 이름")
    keywords: Optional[List[str]] = Field(None, description="문제와 관련된 키워드 목록")
    tags: Optional[List[str]] = Field(
        None, description="문제 관련 태그 목록 (예: 문해력, 논리력)"
    )


# 수정 요청용 스키마 (모든 필드 Optional)
class QuestionUpdate(BaseModel):
    type: Optional[QuestionType] = Field(None, description="문제 유형")
    difficulty_level: Optional[DifficultyLevel] = Field(None, description="문제 난이도")
    question: Optional[str] = Field(None, description="문제 본문")
    options: Optional[List[str]] = Field(None, description="객관식 선택지")
    answer: Optional[str] = Field(None, description="정답")
    explanation: Optional[str] = Field(None, description="해설")
    document_id: int = Field(..., description="문제가 속한 문서의 고유 ID")
    tags: Optional[List[str]] = Field(None, description="태그 목록")
