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
문제는 다음 태그 중 하나씩을 반드시 포함하여 생성해 주세요:

1. **"이해력"** - 기본 개념과 정의 파악
   - 용어 정의, 기본 개념 설명, 단순 암기형 문제
   - 예: "ServiceFLOW의 주요 목적은 무엇인가?", "AGS 인력의 역할을 설명하시오"

2. **"분석력"** - 정보 분해 및 관계 파악  
   - 구성요소 분석, 프로세스 단계별 분석, 비교/대조 문제
   - 예: "프로세스의 각 단계별 특징을 분석하시오", "두 시스템의 차이점을 분석하시오"

3. **"문제해결력"** - 실무 상황 해결 방안 제시
   - 트러블슈팅, 해결방안 제시, 실무 적용 문제
   - 예: "로그인 오류 발생 시 해결 절차는?", "문의 접수 시 필요한 조치를 제시하시오"

4. **"추론력"** - 주어진 정보로부터 결론 도출
   - 원인 추론, 결과 예측, 패턴 파악 문제
   - 예: "이 오류가 발생한 원인을 추론하시오", "다음 단계에서 예상되는 결과는?"

5. **"논리력"** - 논리적 사고와 순서 정립
   - 절차 순서, 논리적 관계, 조건부 사고 문제
   - 예: "올바른 절차 순서를 나열하시오", "조건에 따른 처리 방식을 논리적으로 설명하시오"

각 태그별로 **최소 1개 이상의 문제가 반드시 포함**되어야 하며, 전체 문제 수를 이 다섯 개 태그에 대해 **가능한 한 균등하게 분배**해 주세요.
(예: 10문제라면 각 태그별 2문제씩, 7문제라면 각 태그별 1문제씩 배분 후 남은 2문제는 임의 태그에 할당)

생성되는 각 문제의 tags 필드에는 위의 태그 중 해당 문제에 맞는 태그 1개만 기입하세요.

**문제 생성 시 주의사항**:
- 위의 중요 키워드들을 활용하여 문제를 구성하세요
- 주요 주제와 관련된 실무적 내용을 포함하세요
- 이미지가 있다면 이미지 내용과 연계한 문제를 만드세요
- 단순하게 문제의 출처를 묻는 문제는 제외해주세요

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

**📝 문제 생성 가이드라인**:
1. **전체 테스트 계획과의 일관성**: 위에 제시된 전체 테스트의 목적과 주제에 부합하는 문제를 생성하세요
2. **키워드 활용**: 전체 핵심 키워드와 문서별 키워드를 적절히 조합하여 문제에 포함하세요
3. **주제 연계**: 전체 주요 주제와 문서별 주제를 연결하는 종합적 사고를 요구하는 문제를 만드세요
4. **실무 적용성**: 제시된 테스트 목적에 맞는 실무 적용 능력을 평가할 수 있는 문제를 구성하세요
5. **이미지 연계**: 이미지가 있다면 문서의 핵심 내용과 연계하여 문제를 생성하세요
6. **출처 문제 제외**: 단순하게 문제 출처를 묻는 문제는 제외해주세요
7. 출력 시 마크다운 형식은 사용하지 마세요. 일반 텍스트로 문제를 작성해주세요.


**🎯 특별 요구사항**:
- 단순 암기보다는 **이해와 적용**을 평가하는 문제 우선
- 여러 문서의 내용을 **종합적으로 연결**하는 사고를 요구하는 문제 포함
- 전체 테스트 맥락에서 **중요도가 높은** 개념을 중심으로 문제 구성
- **실무 시나리오**를 활용한 문제 생성 권장

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
    "tags": ["이해력"],
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
    "tags": ["분석력"],
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

필수 조건:
1. 응답은 반드시 유효한 JSON 배열 형식이어야 합니다.
2. type 필드는 "OBJECTIVE" 또는 "SUBJECTIVE" 중 하나여야 합니다.
3. difficulty_level 필드는 반드시 '{difficulty}'를 사용해야 합니다.
4. 객관식 문제는 options 필드를 가져야 합니다.
5. 주관식 문제는 options 필드를 포함하지 않아야 합니다.
6. tags는 ["분석력", "문제해결력", "추론력", "이해력", "논리력"] 중에서 1개 선택해주세요.
7. 주관식 문제는 grading_criteria 필드를 반드시 포함해야 합니다.
8. test_context 필드를 모든 문제에 포함하여 메타데이터를 제공해주세요.
"""
