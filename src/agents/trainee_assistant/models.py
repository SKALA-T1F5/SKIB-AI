from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

class MessageType(Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"

class QuestionType(Enum):
    OBJECTIVE = "objective"
    SUBJECTIVE = "subjective"

class DifficultyLevel(Enum):
    EASY = "easy"
    NORMAL = "normal"
    HARD = "hard"

@dataclass
class ChatMessage:
    type: MessageType
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class QuestionContext:
    test_id: str
    question_id: str
    question_type: QuestionType
    difficulty_level: DifficultyLevel
    question_text: str
    correct_answer: str
    explanation: str
    document_id: str
    document_name: str
    tags: List[str]
    options: Optional[List[str]] = None  # 객관식 선지
    grading_criteria: Optional[str] = None  # 주관식 채점 기준

@dataclass
class SearchResult:
    content: str
    source: str
    score: float
    metadata: Optional[Dict[str, Any]] = None