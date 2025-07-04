"""
Question Generator Prompts
"""

from typing import Dict, List, Optional


def get_vision_prompt(
    source: str,
    page: str,
    difficulty: str,
    num_objective: int,
    num_subjective: int,
    keywords: list = None,
    main_topics: list = None,
    test_config: dict = None,
) -> str:
    """
    GPT-4 Vision용 문제 생성 프롬프트

    Args:
        source: 문서 파일명
        page: 페이지 번호
        difficulty: 난이도 (EASY, NORMAL, HARD)
        num_objective: 객관식 문제 수
        num_subjective: 주관식 문제 수
        keywords: 키워드 목록
        main_topics: 주요 주제 목록
        test_config: 테스트 설정

    Returns:
        str: 프롬프트 문자열
    """
    # 키워드와 주제 정보 추가
    keyword_info = ""
    if keywords:
        keyword_info += f"\n\n**중요 키워드**: {', '.join(keywords[:10])}"
    if main_topics:
        keyword_info += f"\n**주요 주제**: {', '.join(main_topics[:5])}"

    # 테스트 설정 정보 추가
    test_info = ""
    if test_config:
        if test_config.get("test_summary"):
            test_info += f"\n\n**테스트 목적**: {test_config['test_summary'][:200]}..."
        if test_config.get("topics"):
            test_info += f"\n**평가 주제**: {', '.join(test_config['topics'][:3])}"

    return f


"""
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
        7.  `tags`는 문제의 핵심 내용을 나타내는 키워드를 ["분석력", "문제해결력", "추론력", "이해력", "논리력", "문해력", "수리력", "창의력"] 중에서 1개 선택하여 리스트로 제공해주세요.
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
