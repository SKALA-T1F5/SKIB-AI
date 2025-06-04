from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


# Enum 정의
class QuestionType(str, Enum):
    objective = "객관식"
    subjective = "서술형"

class DifficultyLevel(str, Enum):
    easy = "EASY"
    normal = "NORMAL"
    hard = "HARD"

class QuestionConfig(BaseModel):
    documentPath: str
    configuredObjectiveCount: int
    configuredSubjectiveCount: int


# 공통 베이스 모델
class QuestionResponse(BaseModel):
    type: QuestionType = Field(..., description="문제 유형 (객관식 또는 서술형)")
    difficulty_level: DifficultyLevel = Field(..., description="문제 난이도")
    question: str = Field(..., description="문제 본문 텍스트")
    options: Optional[List[str]] = Field(None, description="객관식 선택지 (type이 객관식인 경우)")
    answer: str = Field(..., description="객관식 문제 정답, ")
    explanation: Optional[str] = Field(None, description="정답에 대한 해설")
    document_id: Optional[str] = Field(None, description="문제가 출제된 문서 ID")
    tags: Optional[List[str]] = Field(None, description="문제 관련 태그 목록 (예: 문해력, 논리력)")



# 수정 요청용 스키마 (모든 필드 Optional)
class QuestionUpdate(BaseModel):
    type: Optional[QuestionType] = Field(None, description="문제 유형")
    difficulty_level: Optional[DifficultyLevel] = Field(None, description="문제 난이도")
    question: Optional[str] = Field(None, description="문제 본문")
    options: Optional[List[str]] = Field(None, description="객관식 선택지")
    answer: Optional[str] = Field(None, description="정답")
    explanation: Optional[str] = Field(None, description="해설")
    document_id: Optional[str] = Field(None, description="문서 ID")
    tags: Optional[List[str]] = Field(None, description="태그 목록")

