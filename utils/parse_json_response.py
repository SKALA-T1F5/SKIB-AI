import re
import json
from typing import Union, List, Dict

def parse_json_response(raw_content: str) -> Union[Dict, List[Dict]]:
    text_to_parse = raw_content.strip()
    json_candidate_str = None

    # 1. 마크다운 코드블록 추출
    code_block_match = re.search(r"```(?:json)?\s*(.*?)\s*```", text_to_parse, re.DOTALL | re.IGNORECASE)
    if code_block_match:
        json_candidate_str = code_block_match.group(1).strip()
    else:
        # 2. 대괄호/중괄호로 감싼 JSON 추출
        first_bracket_idx = text_to_parse.find('[')
        first_curly_idx = text_to_parse.find('{')
        start_idx = -1
        if first_bracket_idx != -1 and (first_curly_idx == -1 or first_bracket_idx < first_curly_idx):
            start_idx = first_bracket_idx
        elif first_curly_idx != -1:
            start_idx = first_curly_idx
        if start_idx != -1:
            last_bracket_idx = text_to_parse.rfind(']')
            last_curly_idx = text_to_parse.rfind('}')
            end_idx = -1
            if text_to_parse[start_idx] == '[' and last_bracket_idx > start_idx:
                end_idx = last_bracket_idx
            elif text_to_parse[start_idx] == '{' and last_curly_idx > start_idx:
                end_idx = last_curly_idx
            if end_idx != -1:
                json_candidate_str = text_to_parse[start_idx : end_idx + 1]
            else:
                json_candidate_str = text_to_parse
        else:
            json_candidate_str = text_to_parse

    if json_candidate_str is None:
        json_candidate_str = text_to_parse

    json_final_str_to_parse = json_candidate_str.strip()
    if not json_final_str_to_parse:
        raise ValueError("❌ JSON 파싱 실패: 최종 추출된 문자열이 비어 있습니다.")

    try:
        parsed_data = json.loads(json_final_str_to_parse)
    except json.JSONDecodeError as e:
        # generated_questions fallback
        try:
            outer_obj = json.loads(raw_content.strip())
            if isinstance(outer_obj, dict) and "generated_questions" in outer_obj and isinstance(outer_obj["generated_questions"], list):
                return outer_obj["generated_questions"]
        except json.JSONDecodeError:
            pass
        raise ValueError(f"❌ JSON 파싱 실패: {e}\n\n최종 파싱 시도 문자열 (앞 200자):\n{json_final_str_to_parse[:200]}\n\n원본 LLM 응답 (앞 200자):\n{raw_content.strip()[:200]}")

    # 반환 타입 정리
    if isinstance(parsed_data, list):
        return parsed_data
    elif isinstance(parsed_data, dict):
        # generated_questions 키 fallback
        if "generated_questions" in parsed_data and isinstance(parsed_data["generated_questions"], list):
            return parsed_data["generated_questions"]
        # 단일 객체 반환
        return parsed_data
    else:
        raise ValueError(f"JSON 파싱은 성공했으나, 결과가 리스트 또는 딕셔너리 형식이 아닙니다. 얻은 타입: {type(parsed_data)}")