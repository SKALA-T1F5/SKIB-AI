from typing import List, Literal, Optional, Union

from pydantic import BaseModel


class GradingCriterion(BaseModel):
    score: int
    criteria: str
    example: str
    note: str


class Question(BaseModel):
    id: str
    type: Literal["OBJECTIVE", "SUBJECTIVE"]
    difficultyLevel: str
    question: str
    answer: str
    explanation: Optional[str] = None

    # 🔹 객관식 전용
    options: Optional[List[str]] = None

    # 🔹 주관식 전용
    gradingCriteria: Optional[List[GradingCriterion]] = None

    # 🔹 공통 정보
    documentId: str
    documentName: Optional[str] = None
    keywords: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    generationType: Optional[str] = None


class InitializeTestRequest(BaseModel):
    userId: str
    testQuestions: List[Question]


class QuestionPayload(BaseModel):
    userId: str
    question: str
    id: str
