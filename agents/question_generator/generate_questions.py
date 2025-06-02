# 코드 설명 : gpt-4o 모델 사용하여 문제 생성
# 프롬프트에 문제 생성 가이드 작성 가능

import json
from typing import List, Dict
from openai import OpenAI
from dotenv import load_dotenv
import os

# .env 파일에서 환경 변수 로드
load_dotenv()

# 환경 변수에서 API 키 불러오기
api_key = os.getenv("OPENAI_API_KEY")

# OpenAI 클라이언트 생성
openai_client = OpenAI(api_key=api_key)

import re
import json

def parse_json_response(raw_content: str) -> List[Dict]:
    """
    LLM 응답에서 JSON 리스트를 추출하고 파싱하는 함수
    """
    # 코드 블록 제거 (```json 또는 ``` 포함 여부)
    match = re.search(r"```(?:json)?\s*(\[\s*{.*?}\s*])\s*```", raw_content, re.DOTALL)
    if match:
        json_str = match.group(1).strip()
    else:
        # fallback: 코드 블록 없이 JSON 배열이 그냥 왔을 경우
        json_str = raw_content.strip()

    try:
        parsed = json.loads(json_str)
        if not isinstance(parsed, list):
            raise ValueError("JSON 응답은 리스트 형식이어야 합니다.")
        return parsed
    except json.JSONDecodeError as e:
        raise ValueError(f"❌ JSON 파싱 실패: {e}\n\n응답:\n{json_str}")
    
def localize_enum_fields(question: Dict) -> Dict:
    # 영어 → 한글 매핑
    type_map = {
        "multiple_choice": "객관식",
        "subjective": "서술형"
    }
    difficulty_map = {
        "easy": "EASY",
        "medium": "NORMAL",
        "hard": "HARD"
    }

    question["type"] = type_map.get(question["type"], question["type"])
    question["difficulty_level"] = difficulty_map.get(question["difficulty_level"], question["difficulty_level"])
    return question




# 질문 생성 함수
def generate_question(
    messages: List[Dict],
    source: str,
    page: str,
    num_objective: int = 3,
    num_subjective: int = 3,
    difficulty: int = 3,
) -> list:
    if page == "N/A" or page is None:
        page = "알 수 없음"

    VISION_PROMPT = f"""
    당신은 교육용 문제를 생성하는 AI입니다. 아래 문단은 PDF 문서 "{source}"의 {page}페이지에서 추출된 내용입니다.  
    이 내용을 바탕으로:
    - 객관식 문제 {num_objective}개
    - 주관식 문제 {num_subjective}개
    총 {num_objective + num_subjective}개의 문제를 JSON 형식으로 생성해주세요.

    요청 형식:
    [
    {{
        "type": "multiple_choice" or "subjective",
        "difficulty_level": "easy" | "medium" | "hard",
        "question": "문제 본문",
        "options": ["선택지1", "선택지2", "선택지3", "선택지4"],  # 객관식일 경우만
        "answer": "정답 내용",
        "explanation": "정답 해설",
        "tags": ["문해력", "이해력"]  # 적절히 추가
    }},
    ...
    ]

    조건:
    - 객관식일 경우 'options'를 반드시 포함해주세요.
    - 주관식일 경우 'options'를 포함하지 마세요.
    - 각 문제는 독립적으로 의미가 있어야 하며, 실제 시험에 사용할 수 있어야 합니다.
    - JSON 형식은 Python에서 바로 `json.loads()` 할 수 있도록 유효한 형태여야 합니다.
    - 각 문제의 tags는 문제를 바탕으로 ["분석력", "문제해결력", "추론력", "이해력", "논리력"] 중에서 해당하는 것으로 적절히 선택해주세요.
    """


    full_prompt = [{"type": "text", "text": VISION_PROMPT}] + messages

    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": full_prompt}],
        temperature=0.3,
    )

    raw_content = response.choices[0].message.content.strip()

    print(f"LLM 응답:\n{raw_content}")

    parsed_questions = parse_json_response(raw_content)
    

    processed_questions = []
    for q in parsed_questions:
        q["document_id"] = source
        localized = localize_enum_fields(q)
        processed_questions.append(localized)
    return processed_questions
