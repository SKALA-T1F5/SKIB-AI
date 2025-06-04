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
    Extracts and parses a JSON list from the LLM's raw response string.
    Handles cases with or without markdown code blocks and surrounding text.
    """
    text_to_parse = raw_content.strip()
    json_candidate_str = None

    # Attempt 1: Check if the entire string is a markdown code block.
    # ^ and $ ensure the entire string matches this pattern.
    code_block_match_full = re.search(r"^```(?:json)?\\s*(.*?)\\s*```$", text_to_parse, re.DOTALL | re.IGNORECASE)
    if code_block_match_full:
        json_candidate_str = code_block_match_full.group(1).strip()
        print(f"Info: Extracted from fully matched markdown code block: '{json_candidate_str[:100]}...'")
    else:
        # Attempt 2: Try to find an embedded markdown code block (e.g., surrounded by other text).
        code_block_match_embedded = re.search(r"```(?:json)?\\s*(.*?)\\s*```", text_to_parse, re.DOTALL | re.IGNORECASE)
        if code_block_match_embedded:
            json_candidate_str = code_block_match_embedded.group(1).strip()
            print(f"Info: Extracted from embedded markdown code block: '{json_candidate_str[:100]}...'")
        else:
            # Attempt 3: No clear code block found. Fallback to finding the outermost JSON structure based on brackets/curlies.
            first_bracket_idx = text_to_parse.find('[')
            first_curly_idx = text_to_parse.find('{')

            start_idx = -1
            if first_bracket_idx != -1 and (first_curly_idx == -1 or first_bracket_idx < first_curly_idx):
                start_idx = first_bracket_idx
            elif first_curly_idx != -1:
                start_idx = first_curly_idx

            if start_idx != -1:
                # Found a potential start. Now find the corresponding end.
                # This heuristic assumes the main JSON content is between the first relevant opening bracket/curly
                # and its corresponding last closing bracket/curly.
                # It's not foolproof for all complex/malformed strings but works for many LLM outputs.
                last_bracket_idx = text_to_parse.rfind(']')
                last_curly_idx = text_to_parse.rfind('}')
                
                end_idx = -1
                # If it starts with '[', look for the last ']'.
                if text_to_parse[start_idx] == '[' and last_bracket_idx > start_idx:
                    end_idx = last_bracket_idx
                # If it starts with '{', look for the last '}'.
                elif text_to_parse[start_idx] == '{' and last_curly_idx > start_idx:
                    end_idx = last_curly_idx
                
                # If couldn't find a specific match, try a more general last bracket/curly
                if end_idx == -1 :
                    potential_ends = []
                    if last_bracket_idx > start_idx : potential_ends.append(last_bracket_idx)
                    if last_curly_idx > start_idx : potential_ends.append(last_curly_idx)
                    if potential_ends: end_idx = max(potential_ends)

                if end_idx != -1:
                    json_candidate_str = text_to_parse[start_idx : end_idx + 1]
                    print(f"Info: Heuristically extracted by finding first/last brackets/curlies: '{json_candidate_str[:100]}...'")
                else:
                    print(f"Warning: Found JSON start but no corresponding end. Raw text: '{text_to_parse[:200]}...'")
                    json_candidate_str = text_to_parse # Fallback to trying to parse the (stripped) original text
            else:
                print(f"Warning: No JSON start ('[' or '{{') found. Raw text: '{text_to_parse[:200]}...'")
                json_candidate_str = text_to_parse # Fallback
    
    if json_candidate_str is None: # Should ideally not be None if text_to_parse was not empty
        json_candidate_str = text_to_parse

    json_final_str_to_parse = json_candidate_str.strip()
    if not json_final_str_to_parse:
        raise ValueError("❌ JSON 파싱 실패: 최종 추출된 문자열이 비어 있습니다.")

    try:
        parsed_data = json.loads(json_final_str_to_parse)
    except json.JSONDecodeError as e:
        print(f"Initial parsing failed for: '{json_final_str_to_parse[:200]}...'. Error: {e}. Trying 'generated_questions' fallback.")
        try:
            outer_obj = json.loads(raw_content.strip()) # Try parsing original raw_content for the fallback structure
            if isinstance(outer_obj, dict) and "generated_questions" in outer_obj and isinstance(outer_obj["generated_questions"], list):
                print("Info: Parsed using 'generated_questions' key fallback on raw_content.")
                return outer_obj["generated_questions"]
        except json.JSONDecodeError:
            pass 
        raise ValueError(f"❌ JSON 파싱 실패: {e}\\n\\n최종 파싱 시도 문자열 (앞 200자):\\n{json_final_str_to_parse[:200]}\\n\\n원본 LLM 응답 (앞 200자):\\n{raw_content.strip()[:200]}")

    if isinstance(parsed_data, list):
        return parsed_data
    elif isinstance(parsed_data, dict):
        if all(key in parsed_data for key in ["type", "difficulty_level", "question"]): 
            print("Warning: LLM returned a single JSON object, but a list was expected. Wrapping it in a list.")
            return [parsed_data]
        elif "generated_questions" in parsed_data and isinstance(parsed_data["generated_questions"], list):
             print("Info: LLM returned an object with 'generated_questions' list.")
             return parsed_data["generated_questions"]
        else:
            raise ValueError(f"JSON 파싱은 성공했으나, 결과가 리스트 또는 예상된 객체 형식이 아닙니다. 얻은 타입: {type(parsed_data)}")
    else:
        raise ValueError(f"JSON 파싱은 성공했으나, 결과가 리스트 또는 딕셔너리 형식이 아닙니다. 얻은 타입: {type(parsed_data)}")

# type 및 difficulty_level 필드를 한글로 변환하는 함수 (새로운 함수)
def localize_enum_fields(question: Dict) -> Dict:
    # 영어 → 한글 매핑
    type_map = {
        "OBJECTIVE": "객관식",       # 변경: "multiple_choice" -> "OBJECTIVE"
        "SUBJECTIVE": "서술형",      # 변경: "subjective" 유지 또는 "SUBJECTIVE"로 통일
        # 이전 버전 호환성 또는 다양한 LLM 출력에 대응하기 위한 추가 매핑
        "multiple_choice": "객관식", 
        "MULTIPLE_CHOICE": "객관식"
    }
    difficulty_map = {
        "EASY": "하",               # 변경: "easy" -> "EASY" (대문자 통일)
        "MEDIUM": "중",             # 변경: "medium" -> "MEDIUM"
        "HARD": "상",               # 변경: "hard" -> "HARD"
        # 소문자 입력도 처리 (LLM이 소문자로 반환할 경우 대비)
        "easy": "하",
        "medium": "중",
        "hard": "상"
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
    difficulty: str = "MEDIUM",
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
    "difficulty_level": "{difficulty}",                    # 변경: LLM이 직접 "EASY", "MEDIUM", "HARD" 중 입력된 값을 사용
    "question": "문제의 본문 내용입니다.",
    "options": ["선택지 1번", "선택지 2번", "선택지 3번", "선택지 4번"],  # 객관식(OBJECTIVE) 문제일 경우에만 이 필드를 포함합니다. 주관식(SUBJECTIVE) 문제에는 이 필드를 포함하지 마세요.
    "answer": "문제의 정답입니다.",
    "explanation": "문제에 대한 해설입니다.",
    "tags": ["태그1"]  # 문제 내용과 관련된 태그를 1개 포함하세요. 예: ["문해력"], ["추론력"], ["이해력"]
  }}
  // 여기에 추가 문제 객체들이 올 수 있습니다.
]

필수 조건:
1.  응답은 반드시 유효한 JSON 배열 (리스트) 형식이어야 합니다. JSON 객체로 감싸지 마세요.
2.  `type` 필드는 "OBJECTIVE" 또는 "SUBJECTIVE" 중 하나여야 합니다.
3.  `difficulty_level` 필드는 반드시 입력된 난이도 값인 '{difficulty}' (EASY, MEDIUM, HARD 중 하나)를 그대로 사용해야 합니다.
4.  객관식 문제("OBJECTIVE")는 `options` 필드 (선택지 4개 포함)를 가져야 합니다.
5.  주관식 문제("SUBJECTIVE")는 `options` 필드를 포함하지 않아야 합니다. (필드 자체가 없어야 함)
6.  모든 문제는 `type`, `difficulty_level`, `question`, `answer`, `explanation`, `tags` 필드를 가져야 합니다.
7.  `tags`는 문제의 핵심 내용을 나타내는 키워드를 ["분석력", "문제해결력", "추론력", "이해력", "논리력", "문해력", "수리력", "창의력"] 중에서 1개 선택하여 리스트로 제공해주세요.
"""

    full_prompt = [{"type": "text", "text": VISION_PROMPT}] + messages

    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": full_prompt}],
        temperature=0.3,
    )

    raw_content = response.choices[0].message.content.strip()

    print(f"LLM 응답 (앞 200자):\n{raw_content[:200]}")

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
        
    return processed_questions
