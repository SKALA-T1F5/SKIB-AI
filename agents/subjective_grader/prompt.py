# agents/subjective_grader/prompt.py

from typing import List


# 1. 시스템 프롬프트 정의
# AI의 역할과 응답 형식을 지정합니다.
SYSTEM_PROMPT = """
Score the answer (0–5) based on the grading criteria.
Respond in JSON with 'score' only.
"""

# 2. 사용자 프롬프트 생성 함수
# 사용자 답변과 채점 기준을 받아 AI가 이해할 수 있는 프롬프트 문자열을 생성합니다.
def build_user_prompt(user_answer: str, criteria_text: str) -> str:
    return f"""
Here is the user's answer:
\"\"\"{user_answer}\"\"\"

Here are the grading criteria:
{criteria_text}

Evaluate which criterion the answer best matches,  
and return **only** the score in JSON format.

Example:
{{ "score": 3 }}
"""
