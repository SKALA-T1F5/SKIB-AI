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

    return f"""🎓 **교육 목적 전용 문제 생성**

당신은 기업 교육 및 학습 평가를 위한 전문 문제 생성 AI입니다. 이는 순수한 교육 목적의 평가 도구 개발을 위한 작업입니다.

**문서 정보**: PDF 문서 "{source}"의 {page}페이지에서 추출된 교육 자료입니다.{keyword_info}{test_info}

**생성 요청**: 이 교육 자료를 바탕으로 학습자의 이해도를 평가하기 위한 난이도 '{difficulty}' 수준의 다음 문제들을 생성해주세요:
- 객관식 문제 ({num_objective}개)
- 서술형 문제 ({num_subjective}개)

**문제 태그별 생성 조건**:
문제는 다음 태그 중 하나를 반드시 포함하여 생성하세요. 각 태그별 예시도 참고하세요.

교육 목표를 인지적 복잡성 수준에 따라 6단계로 나눈 체계로, 단계가 높을수록 사고의 수준이 높아짐을 의미합니다.

1. Remember (기억): 사실, 개념, 정의 등을 단순히 회상
2. Understand (이해): 정보를 해석, 요약, 설명
3. Apply (적용): 지식을 새로운 상황에 사용
4. Analyze (분석): 정보의 구성요소를 구별, 관계 분석
5. Evaluate (평가): 판단 기준으로 평가, 비판적 사고
6. Create (창조): 새로운 구조, 아이디어, 제품을 생성

태그별 문제 예시
1. Remember
“이 개념의 정의는 무엇인가요?”
“문서에서 언급한 3가지 주요 요소는 무엇인가요?”

2. Understand
“이 개념을 자신의 말로 설명해보세요.”
“이 프로세스가 어떻게 작동하는지 요약하세요.”

3. Apply
“이 공식을 사용해 다음 사례를 계산해보세요.”
“이 방법론을 사용해 A 문제를 해결하는 절차를 작성해보세요.”

4. Analyze
“이 사례의 핵심 원인을 찾아보세요.”
“이 데이터의 패턴을 분석해 보고 추세를 설명하세요.”

5. Evaluate
“이 두 가지 접근 방식을 비교하고 더 적합한 것을 선택해 이유를 설명하세요.”
“이 프로젝트 제안서의 장단점을 평가하세요.”

6. Create
“이 개념을 활용해 새로운 문제 해결 방안을 제안해보세요.”
“이 데이터를 기반으로 시각화 대시보드를 설계해보세요.”

각 태그별 최소 1개 이상 포함하고, 전체 문제 수를 다섯 개 태그에 균등하게 분배하세요.
모든 문제는 **이해→적용→분석→평가** Bloom’s Taxonomy 단계를 고려해 구성하세요.

**📝 문제 생성 가이드라인**:
1. **전체 테스트 계획과의 일관성**: 위에 제시된 전체 테스트의 목적과 주제에 부합하는 문제를 생성하세요
2. **키워드 활용**: 전체 핵심 키워드와 문서별 키워드를 적절히 조합하여 문제에 포함하세요
3. **주제 연계**: 전체 주요 주제와 문서별 주제를 연결하는 종합적 사고를 요구하는 문제를 만드세요
4. **실무 적용성**: 제시된 테스트 목적에 맞는 실무 적용 능력을 평가할 수 있는 문제를 구성하세요
5. **이미지 연계**: 이미지가 포함되면 이미지 내용 연계 문제 최소 1개 이상 생성하세요
6. **출처 문제 제외**: 단순 문제 출처 확인 문제는 제외해주세요
7. 출력 시 마크다운 형식은 사용하지 마세요. 일반 텍스트로 문제를 작성해주세요.


**🎯 특별 요구사항**:
- 단순 암기보다는 **이해와 적용**을 평가하는 문제 우선
- 여러 문서의 내용을 **종합적으로 연결**하는 사고를 요구하는 문제 포함
- 전체 테스트 맥락에서 **중요도가 높은** 개념을 중심으로 문제 구성
- **실무 시나리오**를 활용한 문제 생성 권장

필수 조건:
1. 응답은 반드시 유효한 JSON 배열 형식이어야 합니다.
2. type 필드는 "OBJECTIVE" 또는 "SUBJECTIVE" 중 하나여야 합니다.
3. difficulty_level 필드는 반드시 '{difficulty}'를 사용해야 합니다.
4. 객관식 문제는 options 필드를 가져야 합니다.
5. 주관식 문제는 options 필드를 포함하지 않아야 합니다.
6. tags는 ["기억", "이해", "적용", "분석", "평가", "창조"] 중에서 1개만 선택해주세요.
7. 주관식 문제는 grading_criteria 필드를 반드시 포함해야 합니다.
8. test_context 필드를 모든 문제에 포함하여 메타데이터를 제공해주세요.

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
    "tags": ["이해"]
}},
{{
    "type": "SUBJECTIVE",
    "difficulty_level": "{difficulty}",
    "question": "주관식 문제 내용",
    "answer": "모범답안",
    "explanation": "해설",
    "tags": ["분석"],
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
6. tags는 ["기억", "이해", "적용", "분석", "평가", "창조"] 중에서 1개만 선택해주세요.
7. 주관식 문제는 grading_criteria 필드를 반드시 포함해야 합니다.
"""


def get_enhanced_vision_prompt(
    source: str,
    page: str,
    difficulty: str,
    num_objective: int,
    num_subjective: int,
    total_test_plan: Optional[Dict] = None,
    document_test_plan: Optional[Dict] = None,
) -> str:
    """
    Test Plan 정보를 활용한 향상된 문제 생성 프롬프트

    Args:
        source: 문서 파일명
        page: 페이지 번호
        difficulty: 난이도 (EASY, NORMAL, HARD)
        num_objective: 객관식 문제 수
        num_subjective: 주관식 문제 수
        total_test_plan: 전체 테스트 계획 정보
        document_test_plan: 문서별 테스트 계획 정보

    Returns:
        str: 향상된 프롬프트 문자열
    """
    # 전체 테스트 계획 정보 구성
    total_test_info = ""
    if total_test_plan:
        metadata = total_test_plan.get("metadata", {})
        test_plan = total_test_plan.get("test_plan", {})
        aggregated_info = total_test_plan.get("aggregated_info", {})

        total_test_info += f"\n\n**📋 전체 테스트 계획 정보**:"
        if test_plan.get("name"):
            total_test_info += f"\n• 테스트명: {test_plan['name']}"
        if test_plan.get("test_summary"):
            total_test_info += f"\n• 테스트 목적: {test_plan['test_summary']}"
        if test_plan.get("difficulty_level"):
            total_test_info += f"\n• 전체 난이도: {test_plan['difficulty_level']}"
        if test_plan.get("limited_time"):
            total_test_info += f"\n• 제한시간: {test_plan['limited_time']}분"

        # 통합된 키워드와 주제 정보
        if aggregated_info.get("all_keywords"):
            keywords = aggregated_info["all_keywords"][:15]  # 상위 15개
            total_test_info += f"\n• 전체 핵심 키워드: {', '.join(keywords)}"

        if aggregated_info.get("all_topics"):
            topics = aggregated_info["all_topics"][:10]  # 상위 10개
            total_test_info += f"\n• 전체 주요 주제: {', '.join(topics)}"

        if metadata.get("document_names"):
            total_test_info += (
                f"\n• 관련 문서: {', '.join(metadata['document_names'][:3])}"
            )

    # 문서별 테스트 계획 정보 구성
    doc_test_info = ""
    if document_test_plan:
        doc_info = document_test_plan.get("document_info", {})
        content_analysis = document_test_plan.get("content_analysis", {})

        doc_test_info += f"\n\n**📄 현재 문서 특화 정보**:"
        if doc_info.get("source_file"):
            doc_test_info += f"\n• 문서명: {doc_info['source_file']}"

        if content_analysis.get("keywords"):
            doc_keywords = content_analysis["keywords"][:10]
            doc_test_info += f"\n• 문서 핵심 키워드: {', '.join(doc_keywords)}"

        if content_analysis.get("main_topics"):
            doc_topics = content_analysis["main_topics"][:5]
            doc_test_info += f"\n• 문서 주요 주제: {', '.join(doc_topics)}"

        if content_analysis.get("summary"):
            summary = content_analysis["summary"][:300]
            doc_test_info += f"\n• 문서 요약: {summary}..."

    return f"""🎓 **교육 목적 전용 문제 생성**

당신은 기업 교육 및 학습 평가를 위한 전문 문제 생성 AI입니다. 이는 순수한 교육 목적의 평가 도구 개발을 위한 작업입니다.

📄 **문서 정보**: PDF 문서 "{source}"의 {page}페이지에서 추출된 교육 자료입니다.{total_test_info}{doc_test_info}

📝 **생성 요청**: 이 교육 자료를 바탕으로 학습자의 이해도를 평가하기 위한 난이도 '{difficulty}' 수준의 다음 문제들을 생성해주세요:
- 객관식 문제 ({num_objective}개)
- 서술형 문제 ({num_subjective}개)

**문제 태그별 생성 조건**:
문제는 다음 Bloom's Taxonomy 태그 중 하나를 반드시 포함하여 생성하세요.

교육 목표를 인지적 복잡성 수준에 따라 6단계로 나눈 체계로, 단계가 높을수록 사고의 수준이 높아짐을 의미합니다.

1. 기억: 사실, 개념, 정의 등을 단순히 회상
2. 이해: 정보를 해석, 요약, 설명
3. 적용: 지식을 새로운 상황에 사용
4. 분석: 정보의 구성요소를 구별, 관계 분석
5. 평가: 판단 기준으로 평가, 비판적 사고
6. 창조: 새로운 구조, 아이디어, 제품을 생성

각 태그별 최소 1개 이상 포함하고, 전체 문제 수를 6개 태그에 균등하게 분배하세요.

**필수 조건**:
1. 응답은 반드시 유효한 JSON 배열 형식이어야 합니다.
2. type 필드는 "OBJECTIVE" 또는 "SUBJECTIVE" 중 하나여야 합니다.
3. difficulty_level 필드는 반드시 '{difficulty}'를 사용해야 합니다.
4. 객관식 문제는 options 필드를 가져야 합니다.
5. 주관식 문제는 options 필드를 포함하지 않아야 합니다.
6. tags는 ["기억", "이해", "적용", "분석", "평가", "창조"] 중에서 1개만 선택해주세요.
7. 주관식 문제는 grading_criteria 필드를 반드시 포함해야 합니다.
8. test_context 필드를 모든 문제에 포함하여 메타데이터를 제공해주세요.

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
    "tags": ["이해"],
    "test_context": {{
        "related_keywords": ["키워드1", "키워드2"],
        "related_topics": ["주제1"],
        "cross_document": false,
        "practical_application": true
    }}
}},
{{
    "type": "SUBJECTIVE",
    "difficulty_level": "{difficulty}",
    "question": "주관식 문제 내용",
    "answer": "모범답안",
    "explanation": "해설",
    "tags": ["분석"],
    "test_context": {{
        "related_keywords": ["키워드1", "키워드2"],
        "related_topics": ["주제1"],
        "cross_document": true,
        "practical_application": true
    }},
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


"""
