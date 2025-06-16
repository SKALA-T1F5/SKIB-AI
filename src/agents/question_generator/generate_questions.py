# 코드 설명 : gpt-4o 모델 사용하여 문제 생성
# 프롬프트에 문제 생성 가이드 작성 가능

import json
from typing import List, Dict
from openai import OpenAI
from dotenv import load_dotenv
import os
import re
from utils.parse_json_response import parse_json_response

# .env 파일에서 환경 변수 로드
load_dotenv(override=True)

# 환경 변수에서 API 키 불러오기
api_key = os.getenv("OPENAI_API_KEY")

# OpenAI 클라이언트 생성
openai_client = OpenAI(api_key=api_key)



# type 및 difficulty_level 필드를 한글로 변환하는 함수 (새로운 함수)
def localize_enum_fields(question: Dict) -> Dict:
    # 영어 → 한글 매핑
    type_map = {
        "OBJECTIVE": "OBJECTIVE",       # 변경: "multiple_choice" -> "OBJECTIVE"
        "SUBJECTIVE": "SUBJECTIVE",      # 변경: "subjective" 유지 또는 "SUBJECTIVE"로 통일
        # 이전 버전 호환성 또는 다양한 LLM 출력에 대응하기 위한 추가 매핑
    }
    difficulty_map = {
        "easy": "EASY",
        "normal": "NORMAL",
        "hard": "HARD"
    }

    # API 응답 키가 difficulty_level 또는 difficultyLevel 일 수 있음
    difficulty_key_original = None
    if "difficulty_level" in question:
        difficulty_key_original = "difficulty_level"
    elif "difficultyLevel" in question:
        difficulty_key_original = "difficultyLevel"

    if "type" in question:
      question["type"] = type_map.get(question["type"], question["type"])
    
    if difficulty_key_original:
      # difficulty_level 키로 통일해서 저장 (한글화 이후)
      question["difficulty_level"] = difficulty_map.get(question[difficulty_key_original], question[difficulty_key_original])
      if difficulty_key_original != "difficulty_level" and difficulty_key_original in question: # 이미 difficulty_level로 바뀌었으면 삭제 불필요
          del question[difficulty_key_original]
          
    return question


# 질문 생성 함수
def generate_question(
    messages: List[Dict],
    source: str,
    page: str,
    num_objective: int = 3,
    num_subjective: int = 3,
    difficulty: str = "NORMAL",
) -> List[Dict]:
    if page == "N/A" or page is None:
        page = "알 수 없음"

    VISION_PROMPT = f"""
        당신은 교육용 문제를 생성하는 AI입니다. 아래 문단은 PDF 문서 "{source}"의 {page}페이지에서 추출된 내용입니다.  
        이 내용을 바탕으로 요청된 난이도 '{difficulty}' 수준으로 다음 문제들을 생성해주세요:
        - 객관식 문제 ({num_objective}개)
        - 서술형 문제 ({num_subjective}개)
        총 {num_objective + num_subjective}개의 문제를 **반드시 다음 명세에 따른 JSON 리스트 형식**으로 생성해주세요.
        다른 어떤 설명이나 추가 텍스트 없이, 순수한 JSON 배열 문자열만 응답해야 합니다.

        요청 형식 (JSON 배열):
        [
        {{
            "type": "OBJECTIVE" or "SUBJECTIVE",                  # 변경: "multiple_choice" -> "OBJECTIVE"
            "difficulty_level": "{difficulty}",                    # 변경: LLM이 직접 "EASY", "NORMAL", "HARD" 중 입력된 값을 사용
            "question": "문제의 본문 내용입니다.",
            "options": ["선택지 1번", "선택지 2번", "선택지 3번", "선택지 4번"],  # 객관식(OBJECTIVE) 문제일 경우에만 이 필드를 포함합니다. 주관식(SUBJECTIVE) 문제에는 이 필드를 포함하지 마세요.
            "answer": "문제의 정답입니다.",
            "explanation": "문제에 대한 해설입니다.",
            "tags": ["태그1"]  # 문제 내용과 관련된 태그를 1개 포함하세요. 예: ["문해력"], ["추론력"], ["이해력"]
            "grading_criteria": [
            {{
                "score": 5,
                "criteria": "해당 점수를 받을 수 있는 조건 설명",
                "keywords_required": ["반드시 포함되어야 할 핵심 키워드"],       # 선택사항
                "keywords_optional": ["포함되면 좋은 참고 키워드"],             # 선택사항
                "example": "모범 답안 예시",
                "note": "채점 시 참고 사항 또는 유의점"
            }},
            {{
                "score": 3,
                "criteria": "...",
                ...
            }},
            ...
            ]
        }}
        // 여기에 추가 문제 객체들이 올 수 있습니다.
        ]

        필수 조건:
        1.  응답은 반드시 유효한 JSON 배열 (리스트) 형식이어야 합니다. JSON 객체로 감싸지 마세요.
        2.  `type` 필드는 "OBJECTIVE" 또는 "SUBJECTIVE" 중 하나여야 합니다.
        3.  `difficulty_level` 필드는 반드시 입력된 난이도 값인 '{difficulty}' (EASY, NORMAL, HARD 중 하나)를 그대로 사용해야 합니다.
        4.  객관식 문제("OBJECTIVE")는 `options` 필드 (선택지 4개 포함)를 가져야 합니다.
        5.  주관식 문제("SUBJECTIVE")는 `options` 필드를 포함하지 않아야 합니다. (필드 자체가 없어야 함)
        6.  모든 문제는 `type`, `difficulty_level`, `question`, `answer`, `explanation`, `tags` 필드를 가져야 합니다.
        7.  `tags`는 문제의 핵심 내용을 나타내는 키워드를 ["분석력", "문제해결력", "추론력", "이해력", "논리력",] 중에서 1개 선택하여 리스트로 제공해주세요.
        8.  주관식 문제("SUBJECTIVE")는 `grading_criteria` 필드를 반드시 포함해야 하며, 이는 아래 형식의 리스트로 구성되어야 합니다:
        [
        {{
            "score": (점수, 예: 5, 3, 2, 0),
            "criteria": (해당 점수를 받을 수 있는 조건 설명),
            "keywords_required": [선택사항, 해당 점수를 받기 위해 반드시 포함되어야 하는 키워드 목록],
            "keywords_optional": [선택사항, 해당 점수를 받을 수 있는 힌트 키워드 목록],
            "example": (모범 답안 예시),
            "note": (채점 참고 사항 또는 유의점)
        }},
        ...
        ]
        - `score`는 5, 3, 2, 0 중 하나로 구성되어야 하며, 각 항목은 독립적인 채점 기준을 설명해야 합니다.
        - `keywords_required` 또는 `keywords_optional`은 각 점수 조건에 따라 선택적으로 제공해주세요.
        - `grading_criteria`는 최소 3개의 점수 단계(예: 5점, 3점, 1점)를 포함해야 합니다.

        """

    full_prompt = [{"type": "text", "text": VISION_PROMPT}] + messages

    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": full_prompt}],
        temperature=0.3,
    )

    raw_content = response.choices[0].message.content.strip()

    print(f"LLM 응답 (앞 200자):\n{raw_content}")

    try:
        parsed_questions = parse_json_response(raw_content)
    except ValueError as e:
        print(f"Error during parsing, returning raw data: {e}")
        return [{"error": str(e), "raw_response": raw_content}]

    processed_questions = []
    for q_idx, q_item in enumerate(parsed_questions):
        if not isinstance(q_item, dict):
            print(f"Warning: Skipping non-dict item in parsed list at index {q_idx}: {str(q_item)[:100]}...")
            continue

        required_keys = ["type", "difficulty_level", "question", "answer", "explanation", "tags"]
        missing_keys = [key for key in required_keys if key not in q_item]
        if missing_keys:
            print(f"Warning: Skipping question due to missing keys {missing_keys} in item: {str(q_item)[:100]}...")
            continue
        
        if q_item.get("type") == "OBJECTIVE" and "options" not in q_item:
            print(f"Warning: Skipping OBJECTIVE question due to missing 'options': {str(q_item)[:100]}...")
            continue

        q_item["document_id"] = source
        q_item["page_number"] = page
        q_item["question_id"] = f"{source}_{page}_{q_idx}"

        processed_questions.append(q_item)
    
    if not processed_questions and parsed_questions:
        print("Warning: All parsed questions were filtered out during post-processing.")
        return [{"error": "All parsed questions were filtered out during post-processing.", "raw_response": raw_content}]
        
    return [localize_enum_fields(q) for q in processed_questions]

