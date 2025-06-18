"""
Question Generator Prompts
"""

def get_vision_prompt(source: str, page: str, difficulty: str, num_objective: int, num_subjective: int) -> str:
    """
    GPT-4 Vision용 문제 생성 프롬프트
    
    Args:
        source: 문서 파일명
        page: 페이지 번호
        difficulty: 난이도 (EASY, NORMAL, HARD)
        num_objective: 객관식 문제 수
        num_subjective: 주관식 문제 수
    
    Returns:
        str: 프롬프트 문자열
    """
    return f"""당신은 교육용 문제를 생성하는 AI입니다. 아래 문단은 PDF 문서 "{source}"의 {page}페이지에서 추출된 내용입니다.  
이 내용을 바탕으로 요청된 난이도 '{difficulty}' 수준으로 다음 문제들을 생성해주세요:
- 객관식 문제 ({num_objective}개)
- 서술형 문제 ({num_subjective}개)
총 {num_objective + num_subjective}개의 문제를 **반드시 다음 명세에 따른 JSON 리스트 형식**으로 생성해주세요.
다른 어떤 설명이나 추가 텍스트 없이, 순수한 JSON 배열 문자열만 응답해야 합니다.

요청 형식 (JSON 배열):
[
{{
    "type": "OBJECTIVE",
    "difficulty_level": "{difficulty}",
    "question": "문제의 본문 내용입니다.",
    "options": ["선택지 1번", "선택지 2번", "선택지 3번", "선택지 4번"],
    "answer": "문제의 정답입니다.",
    "explanation": "문제에 대한 해설입니다.",
    "tags": ["이해력"]
}},
{{
    "type": "SUBJECTIVE",
    "difficulty_level": "{difficulty}",
    "question": "주관식 문제 내용",
    "answer": "모범답안",
    "explanation": "해설",
    "tags": ["분석력"],
    "grading_criteria": [
        {{
            "score": 5,
            "criteria": "완전한 답안 조건",
            "keywords_required": ["필수키워드1", "필수키워드2"],
            "example": "모범답안 예시",
            "note": "채점 시 주의사항"
        }},
        {{
            "score": 3,
            "criteria": "부분적 답안 조건",
            "keywords_optional": ["선택키워드1"],
            "example": "부분답안 예시",
            "note": "부분 점수 기준"
        }}
    ]
}}
]

필수 조건:
1. 응답은 반드시 유효한 JSON 배열 형식이어야 합니다.
2. type 필드는 "OBJECTIVE" 또는 "SUBJECTIVE" 중 하나여야 합니다.
3. difficulty_level 필드는 반드시 '{difficulty}'를 사용해야 합니다.
4. 객관식 문제는 options 필드를 가져야 합니다.
5. 주관식 문제는 options 필드를 포함하지 않아야 합니다.
6. tags는 ["분석력", "문제해결력", "추론력", "이해력", "논리력"] 중에서 1개 선택해주세요.
7. 주관식 문제는 grading_criteria 필드를 반드시 포함해야 합니다.
"""