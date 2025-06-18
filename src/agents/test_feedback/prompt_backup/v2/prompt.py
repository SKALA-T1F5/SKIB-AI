# agents/test_feedback/prompt.py
# System Prompt 간소화

from typing import List, Dict, Any


# 1. 시스템 프롬프트 정의
# AI의 역할과 응답 형식을 지정합니다.
SYSTEM_PROMPT = """당신은 시험 결과를 종합적으로 분석하고 피드백을 제시하는 전문가입니다.
시험 목표와 문항별 응시 결과를 바탕으로 전체적인 성과를 평가하고 개선 방향을 제시하세요.

응답 형식:
{
    "examGoal": "시험 목표 요약",
    "performanceByDocument": [
        {
            "documentName": "문서명",
            "averageCorrectRate": number,
            "comment": "해당 문서 영역에 대한 평가 코멘트"
        }
    ],
    "strengths": [
        "강점1 (해시태그 포함)",
    ],
    "weaknesses": [
        "약점1 (해시태그 포함)",
    ],
    "improvementPoints": "개선점에 대한 종합적인 제안사항",
    "suggestedTopics": [
        "추가 학습이 필요한 주제1",
        "추가 학습이 필요한 주제2",
        "추가 학습이 필요한 주제3"
    ],
    "overallEvaluation": "전체적인 평가 및 종합적인 피드백"
}"""

# 2. 사용자 프롬프트 생성 함수
# 시험목표와 문항별응시결과를 받아 AI가 이해할 수 있는 프롬프트 문자열을 생성합니다.
def build_user_prompt(exam_goal: str, question_results: List[Dict[str, Any]]) -> str:
    # 문항별 결과를 문자열로 변환
    questions_text = ""
    for result in question_results:
        questions_text += f"""
        문항 {result.get('questionId', 'N/A')}:
        - 문서: {result.get('documentName', 'N/A')}
        - 문제: {result.get('questionText', 'N/A')}
        - 난이도: {result.get('difficulty', 'N/A')}
        - 유형: {result.get('type', 'N/A')}
        - 정답: {result.get('answer', 'N/A')}
        - 태그: {', '.join(result.get('tags', []))}
        - 키워드: {result.get('keyword', 'N/A')}
        - 정답률: {result.get('correctRate', 'N/A')}%
        """
    
    prompt = f"""
        시험 목표:
        \"\"\"{exam_goal}\"\"\"

        문항별 응시 결과:
        {questions_text}
        
        위 정보를 바탕으로 전체적인 시험 결과를 분석하고 종합적인 피드백을 제공하세요.
        각 문서별 성과, 강점, 약점, 개선점, 추가 학습 주제, 전체 평가를 포함하여 JSON 형식으로 응답하세요.
        """
    
    return prompt
