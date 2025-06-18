# agents/test_feedback/prompt.py

from typing import List, Dict, Any


# 1. 시스템 프롬프트 정의
# AI의 역할과 응답 형식을 지정합니다.
SYSTEM_PROMPT = """당신은 시험 결과를 종합적으로 분석하고 피드백을 제시하는 전문가입니다.
시험 목표와 문항별 응시 결과를 바탕으로 전체적인 성과를 평가하고 개선 방향을 제시하세요.

응답 형식:
{
    "overall_score": number (0-100),
    "achievement_level": "상/중/하",
    "test_analysis": {
        "strengths": ["강점1", "강점2"],
        "weaknesses": ["약점1", "약점2"],
        "improvement_areas": ["개선영역1", "개선영역2"]
    },
    "detailed_feedback": {
        "overall_performance": "전체적인 성과 평가",
        "goal_achievement": "시험 목표 달성도 평가",
        "recommendations": ["권장사항1", "권장사항2", "권장사항3"]
    },
    "question_analysis": [
        {
            "question_id": "문항번호",
            "performance": "해당 문항 성과 평가",
            "suggestion": "해당 문항 개선 제안"
        }
    ]
}"""

# 2. 사용자 프롬프트 생성 함수
# 시험목표와 문항별응시결과를 받아 AI가 이해할 수 있는 프롬프트 문자열을 생성합니다.
def build_user_prompt(test_goal: str, question_results: List[Dict[str, Any]]) -> str:
    # 문항별 결과를 문자열로 변환
    questions_text = ""
    for i, result in enumerate(question_results, 1):
        questions_text += f"""
        문항 {i}:
        - 학생 답변: {result.get('student_answer', 'N/A')}
        - 정답: {result.get('correct_answer', 'N/A')}
        - 점수: {result.get('score', 'N/A')}
        - 채점 기준: {result.get('criteria', 'N/A')}
        """
    
    prompt = f"""
        시험 목표:
        \"\"\"{test_goal}\"\"\"

        문항별 응시 결과:
        {questions_text}
        
        위 정보를 바탕으로 전체적인 시험 결과를 분석하고 종합적인 피드백을 제공하세요.
        JSON 형식으로 응답하세요.
        """
    
    return prompt
