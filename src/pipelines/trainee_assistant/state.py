from typing import List, Optional, TypedDict

from api.trainee_assistant.schemas.trainee_assistant import Question


class ChatState(TypedDict):
    user_id: str
    question: str
    question_id: str
    document_name: Optional[str]
    test_questions: List[Question]
    question_data: Optional[Question]  # 추가
    chroma_docs: Optional[List[dict]]
    answer: Optional[str]
