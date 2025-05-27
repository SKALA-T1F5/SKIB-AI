# 코드 설명 : gpt-4o 모델 사용하여 문제 생성
# 프롬프트에 문제 생성 가이드 작성 가능

from typing import List, Dict
from openai import OpenAI
import os

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# 질문 생성 함수
def generate_question(
    messages: List[Dict],
    source: str,
    page: str,
    question_type: str = "both",
    difficulty: int = 3,
) -> dict:
    if page == "N/A" or page is None:
        page = "알 수 없음"

    VISION_PROMPT = f"""
아래 내용은 PDF 문서 "{source}"의 {page}페이지에서 추출된 것입니다. 
이 내용을 바탕으로 난이도 {difficulty} 수준의 객관식 문제 3개와 주관식 문제 3개를 생성해주세요.

문제 형식:
문제: ...
(객관식의 경우 보기)
정답: ...
이유: ...
출처: {source}, {page}페이지

요구 사항:
- 문제 유형: 객관식 5문제 + 주관식 5문제 (총 10문제)
- 난이도: {difficulty} (1=쉬움, 5=어려움)
- 모든 문제에 정답과 이유 반드시 포함
- 주관식 문제는 정답 기준을 서술형으로 기술해주세요(3점 기준, 2점 기준, 1점 기준, 0점 기준)
- 형식이 명확하게 구분되도록 작성해주세요
"""

    full_prompt = [{"type": "text", "text": VISION_PROMPT}] + messages

    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": full_prompt}],
        temperature=0.3,
    )

    return {"raw": response.choices[0].message.content.strip()}
