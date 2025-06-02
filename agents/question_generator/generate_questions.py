# 코드 설명 : gpt-4o 모델 사용하여 문제 생성
# 프롬프트에 문제 생성 가이드 작성 가능

import json
from typing import List, Dict
from openai import OpenAI
from dotenv import load_dotenv
import os
import re

# .env 파일에서 환경 변수 로드
load_dotenv(override=True)

# 환경 변수에서 API 키 불러오기
api_key = os.getenv("OPENAI_API_KEY")

# OpenAI 클라이언트 생성
openai_client = OpenAI(api_key=api_key)


# LLM 응답에서 JSON 리스트를 추출하고 파싱하는 함수 (새로운 함수)
def parse_json_response(raw_content: str) -> List[Dict]:
    """
    LLM 응답에서 JSON 리스트를 추출하고 파싱하는 함수
    """
    # 코드 블록 제거 (```json 또는 ``` 포함 여부)
    match = re.search(r"```(?:json)?\\s*(\\[\\s*{.*?}\\s*])\\s*```", raw_content, re.DOTALL)
    if match:
        json_str = match.group(1).strip()
    else:
        # fallback: 코드 블록 없이 JSON 배열이 그냥 왔을 경우
        # 응답이 리스트로 시작하고 리스트로 끝나는지 간단히 확인
        if raw_content.startswith("[") and raw_content.endswith("]"):
            json_str = raw_content
        else:
            # 만약 전체가 하나의 JSON 객체로 감싸져 있고, 그 안에 리스트가 있다면 처리 (예: {"questions": [...]})
            # 이 부분은 현재 프롬프트와는 맞지 않지만, 더 유연한 파싱을 위해 남겨둘 수 있습니다.
            # 지금 프롬프트는 직접 리스트를 반환하도록 요청하고 있습니다.
            # 좀 더 견고하게 하려면, 여기서 다양한 예외 케이스를 처리해야 합니다.
            print(f"Warning: Response does not seem to be a direct JSON array nor wrapped in ```json ... ```. Trying to parse as is: {raw_content[:200]}...")
            json_str = raw_content # 일단 그대로 시도

    try:
        parsed = json.loads(json_str)
        if not isinstance(parsed, list):
            # 때때로 LLM이 리스트 대신 단일 객체를 반환할 수 있음. 이 경우 리스트로 감싸줌.
            if isinstance(parsed, dict) and all(key in parsed for key in ["type", "difficulty_level", "question"]): # 간단한 검증
                print("Warning: LLM returned a single JSON object, wrapping it in a list.")
                return [parsed]
            raise ValueError("JSON 응답은 리스트 형식이어야 합니다.")
        return parsed
    except json.JSONDecodeError as e:
        # 파싱 실패 시, LLM이 JSON 객체 안에 "generated_questions" 키로 리스트를 반환했는지 확인 (이전 로직 호환성)
        try:
            outer_obj = json.loads(raw_content)
            if isinstance(outer_obj, dict) and "generated_questions" in outer_obj and isinstance(outer_obj["generated_questions"], list):
                print("Info: Parsed using 'generated_questions' fallback.")
                return outer_obj["generated_questions"]
        except json.JSONDecodeError:
            pass # 이중 실패는 아래에서 처리

        raise ValueError(f"❌ JSON 파싱 실패: {e}\n\n응답 (앞 200자):\n{json_str[:200]}")

# type 및 difficulty_level 필드를 한글로 변환하는 함수 (새로운 함수)
def localize_enum_fields(question: Dict) -> Dict:
    # 영어 → 한글 매핑
    type_map = {
        "multiple_choice": "객관식",
        "subjective": "서술형",
        "MULTIPLE_CHOICE": "객관식", # 이전 프롬프트 호환성
        "SUBJECTIVE": "서술형"      # 이전 프롬프트 호환성
    }
    difficulty_map = {
        "easy": "하",
        "medium": "중",
        "hard": "상",
        "EASY": "하",   # 이전 프롬프트 호환성
        "MEDIUM": "중", # 이전 프롬프트 호환성
        "HARD": "상"    # 이전 프롬프트 호환성
    }

    # API 응답 키가 difficulty_level 또는 difficultyLevel 일 수 있음
    difficulty_key = "difficulty_level" if "difficulty_level" in question else "difficultyLevel"

    if "type" in question:
      question["type"] = type_map.get(question["type"], question["type"])
    if difficulty_key in question:
      question["difficulty_level"] = difficulty_map.get(question[difficulty_key], question[difficulty_key])
      if difficulty_key != "difficulty_level": # 키 통일
          del question[difficulty_key]
    return question


# 질문 생성 함수
def generate_question(
    messages: List[Dict],
    source: str,
    page: str,
    num_objective: int = 3,
    num_subjective: int = 3,
    difficulty: int = 3,
) -> List[Dict]:
    if page == "N/A" or page is None:
        page = "알 수 없음"

    VISION_PROMPT = f"""
당신은 교육용 문제를 생성하는 AI입니다. 아래 문단은 PDF 문서 "{source}"의 {page}페이지에서 추출된 내용입니다.  
이 내용을 바탕으로:
- 객관식 문제 {num_objective}개
- 주관식 문제 {num_subjective}개
총 {num_objective + num_subjective}개의 문제를 **반드시 다음 명세에 따른 JSON 리스트 형식**으로 생성해주세요.
다른 어떤 설명이나 추가 텍스트 없이, 순수한 JSON 배열 문자열만 응답해야 합니다.

요청 형식 (JSON 배열):
[
  {{
    "type": "multiple_choice" or "subjective",
    "difficulty_level": "easy" | "medium" | "hard", 
    "question": "문제의 본문 내용입니다.",
    "options": ["선택지 1번", "선택지 2번", "선택지 3번", "선택지 4번"],  # 객관식 문제일 경우에만 이 필드를 포함합니다. 주관식 문제에는 이 필드를 포함하지 마세요.
    "answer": "문제의 정답입니다.",
    "explanation": "문제에 대한 해설입니다.",
    "tags": ["태그1", "태그2"]  # 문제 내용과 관련된 태그를 1개 이상 포함하세요. 예: ["문해력", "논리적 사고"]
  }}
  // 여기에 추가 문제 객체들이 올 수 있습니다.
]

난이도 매핑:
- 입력된 난이도 점수 {difficulty} (1~5점)를 기준으로 "easy", "medium", "hard" 중 하나로 변환하여 `difficulty_level` 필드에 넣어주세요.
  - 1-2점: "easy"
  - 3점: "medium"
  - 4-5점: "hard"

필수 조건:
1.  응답은 반드시 유효한 JSON 배열 (리스트) 형식이어야 합니다. JSON 객체로 감싸지 마세요.
2.  객관식 문제는 `options` 필드 (선택지 4개 포함)를 가져야 합니다.
3.  주관식 문제는 `options` 필드를 포함하지 않아야 합니다. (필드 자체가 없어야 함)
4.  모든 문제는 `type`, `difficulty_level`, `question`, `answer`, `explanation`, `tags` 필드를 가져야 합니다.
5.  `tags`는 문제의 핵심 내용을 나타내는 키워드를 ["분석력", "문제해결력", "추론력", "이해력", "논리력", "문해력", "수리력", "창의력"] 중에서 1개 이상 선택하여 리스트로 제공해주세요.
"""

    full_prompt = [{"type": "text", "text": VISION_PROMPT}] + messages

    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": full_prompt}],
        temperature=0.3,
    )

    raw_content = response.choices[0].message.content.strip()

    print(f"LLM 응답 (앞 200자):\n{raw_content[:200]}")

    # JSON 파싱 로직 변경 (새로운 함수 사용)
    try:
        parsed_questions = parse_json_response(raw_content)
    except ValueError as e:
        print(f"Error during parsing, returning raw data: {e}")
        # 파싱 실패 시, 이전처럼 raw 데이터를 반환할 수 있지만, save_results.py가 리스트를 기대하므로 빈 리스트나 에러 객체 반환 고려
        return [{"error": str(e), "raw_response": raw_content}]


    # 후처리 로직 추가 (새로운 코드 내용)
    processed_questions = []
    for q_idx, q_item in enumerate(parsed_questions):
        if not isinstance(q_item, dict):
            print(f"Warning: Skipping non-dict item in parsed list at index {q_idx}: {str(q_item)[:100]}...")
            continue

        # 필수 필드 검증 강화
        required_keys = ["type", "question", "answer", "explanation", "tags"]
        # difficulty_level은 localize_enum_fields에서 difficultyLevel도 처리하므로 일단 여기서 제외
        
        missing_keys = [key for key in required_keys if key not in q_item]
        if missing_keys:
            print(f"Warning: Skipping question due to missing keys {missing_keys} in item: {str(q_item)[:100]}...")
            continue
        
        if q_item.get("type") == "multiple_choice" and "options" not in q_item:
            print(f"Warning: Skipping multiple_choice question due to missing 'options': {str(q_item)[:100]}...")
            continue

        q_item["document_id"] = source # document_id 추가 (기존 documentId에서 변경됨)
        q_item["page_number"] = page # 페이지 번호 추가 (선택적)
        q_item["question_id"] = f"{source}_{page}_{q_idx}" # 고유 ID 생성 (선택적)

        localized_item = localize_enum_fields(q_item)
        processed_questions.append(localized_item)
    
    if not processed_questions and parsed_questions: # 파싱은 성공했으나 모든 항목이 필터링된 경우
        print("Warning: All parsed questions were filtered out during post-processing.")
        return [{"error": "All parsed questions were filtered out during post-processing.", "raw_response": raw_content}]
        
    return processed_questions
