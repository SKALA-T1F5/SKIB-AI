from typing import Dict, Any, Optional
from src.agents.trainee_assistant.models import QuestionContext, QuestionType, DifficultyLevel

class QuestionContextManager:
    """문제 컨텍스트 관리 클래스"""

    def __init__(self):
        self.current_question_context: Optional[QuestionContext] = None

    def set_question_context(self, question_data: Dict[str, Any]):
        """프론트엔드에서 받은 문제 정보를 설정"""
        question = question_data.get("question", {})

        self.current_question_context = QuestionContext(
            test_id=question_data.get("testId"),
            question_id=question.get("_id", {}).get("$oid") if isinstance(question.get("_id"), dict) else question.get("_id"),
            question_type=QuestionType(question.get("question_type")),
            difficulty_level=DifficultyLevel(question.get("difficultyLevel")),
            question_text=question.get("question"),
            options=question.get("options"),  # Optional[List[str]]
            grading_criteria=question.get("gradingCriteria"),  # Optional[str]
            correct_answer=question.get("answer"),
            explanation=question.get("explanation"),
            document_id=question.get("documentId"),
            document_name=question.get("document_name"),
            tags=question.get("tags", [])
        )

    def get_system_prompt(self) -> str:
        """시스템 프롬프트 생성"""
        if not self.current_question_context:
            return """당신은 시험을 마친 학습자(Trainee)를 위한 AI 어시스턴트입니다. 
학습자가 채점 결과를 보며 궁금한 점이나 추가 학습이 필요한 부분에 대해 질문할 때 도움을 제공합니다."""

        ctx = self.current_question_context

        prompt = f"""당신은 시험을 마친 학습자(Trainee)를 위한 AI 어시스턴트입니다.

현재 문제 정보:
- 문제 유형: {ctx.question_type.value}
- 난이도: {ctx.difficulty_level.value}
- 문제: {ctx.question_text}"""

        if ctx.options:
            prompt += f"\n- 보기 항목: {', '.join(ctx.options)}"

        prompt += f"""
- 정답: {ctx.correct_answer}
- 해설: {ctx.explanation}
- 문서명: {ctx.document_name}
- 평가 태그: {', '.join(ctx.tags)}"""

        if ctx.grading_criteria:
            prompt += f"\n- ※ 주관식 채점 기준: {ctx.grading_criteria}"

        prompt += """

역할:
1. 학습자가 채점 결과를 보며 가지는 궁금증에 답변
2. 틀린 문제나 어려웠던 문제에 대한 추가 설명 제공
3. 정답과 오답의 차이점 명확히 설명
4. 관련 개념이나 학습 포인트 안내
5. 비슷한 유형의 문제 해결 방법 제시
6. 추가 학습 자료나 방향 추천

학습자가 이해하기 쉽게 친근하고 격려하는 톤으로 응답해주세요."""

        return prompt

    def get_context_summary(self) -> Dict[str, Any]:
        """컨텍스트 요약 정보 반환"""
        return {
            "test_id": self.current_question_context.test_id if self.current_question_context else None,
            "question_type": self.current_question_context.question_type.value if self.current_question_context else None,
            "difficulty_level": self.current_question_context.difficulty_level.value if self.current_question_context else None,
            "tags": self.current_question_context.tags if self.current_question_context else []
        }