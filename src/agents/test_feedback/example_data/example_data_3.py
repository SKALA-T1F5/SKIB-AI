# agents/test_feedback/example_data/example_data_3.py
# 사내 연말정산 프로세스 및 시스템 활용 능력 평가 시험 (전체적으로 낮은 정답률, 각 문서 5문항씩)

# exam_goal_3: 사내 연말정산 관련 시험 목표
exam_goal = "사내 연말정산 프로세스 및 시스템 활용 능력을 평가하기 위한 시험입니다. 국세청 간소화 자료 활용, YETA 시스템 입력 방법, 공제 요건 등의 실무 지식을 객관식과 주관식 혼합형으로 확인합니다."

# question_results_3: 문항별 결과
question_results = [
    # 1~5: 국세청 연말정산간소화자료 다운로드 매뉴얼
    {
        "questionId": 1,
        "documentName": "국세청 연말정산간소화자료 다운로드 매뉴얼",
        "questionText": "연말정산 간소화 서비스에서 제공되는 항목이 아닌 것은 무엇인가요?",
        "difficulty": "EASY",
        "type": "OBJECTIVE",
        "answer": "신용카드 발급 이력",
        "tags": ["이해력"],
        "keyword": "간소화 항목",
        "correctRate": 61.3
    },
    {
        "questionId": 2,
        "documentName": "국세청 연말정산간소화자료 다운로드 매뉴얼",
        "questionText": "간소화 자료를 내려받기 위해 필요한 인증 방식은 무엇인가요?",
        "difficulty": "NORMAL",
        "type": "OBJECTIVE",
        "answer": "공동인증서(구 공인인증서)",
        "tags": ["이해력"],
        "keyword": "인증서",
        "correctRate": 54.2
    },
    {
        "questionId": 3,
        "documentName": "국세청 연말정산간소화자료 다운로드 매뉴얼",
        "questionText": "간소화 자료가 제공되지 않는 대표적인 항목 한 가지를 작성하세요.",
        "difficulty": "NORMAL",
        "type": "SUBJECTIVE",
        "answer": "월세 세액공제 자료",
        "tags": ["문제해결력"],
        "keyword": "비제공 항목",
        "correctRate": 41.8
    },
    {
        "questionId": 4,
        "documentName": "국세청 연말정산간소화자료 다운로드 매뉴얼",
        "questionText": "제출서류 확인 시 가장 먼저 확인해야 할 사항은 무엇인가요?",
        "difficulty": "NORMAL",
        "type": "OBJECTIVE",
        "answer": "자료의 수집 여부 및 누락 항목",
        "tags": ["분석력"],
        "keyword": "자료 검토",
        "correctRate": 47.9
    },
    {
        "questionId": 5,
        "documentName": "국세청 연말정산간소화자료 다운로드 매뉴얼",
        "questionText": "의료비 누락 시 처리 방법을 작성하세요.",
        "difficulty": "HARD",
        "type": "SUBJECTIVE",
        "answer": "의료기관 영수증 직접 제출",
        "tags": ["문제해결력"],
        "keyword": "의료비 누락",
        "correctRate": 38.5
    },

    # 6~10: 연말정산시스템(YETA) 매뉴얼
    {
        "questionId": 6,
        "documentName": "연말정산시스템(YETA) 매뉴얼",
        "questionText": "YETA 로그인 후 가장 먼저 해야 하는 절차는 무엇인가요?",
        "difficulty": "EASY",
        "type": "OBJECTIVE",
        "answer": "소득·세액공제신고서 작성",
        "tags": ["이해력"],
        "keyword": "YETA 절차",
        "correctRate": 64.2
    },
    {
        "questionId": 7,
        "documentName": "연말정산시스템(YETA) 매뉴얼",
        "questionText": "부양가족 공제에서 고려할 조건은 무엇인가요?",
        "difficulty": "NORMAL",
        "type": "OBJECTIVE",
        "answer": "소득 요건 충족 여부",
        "tags": ["추론력"],
        "keyword": "부양가족 공제",
        "correctRate": 52.4
    },
    {
        "questionId": 8,
        "documentName": "연말정산시스템(YETA) 매뉴얼",
        "questionText": "자동반영 기능의 이점 한 가지를 작성하세요.",
        "difficulty": "NORMAL",
        "type": "SUBJECTIVE",
        "answer": "중복입력 방지 및 입력 오류 감소",
        "tags": ["이해력"],
        "keyword": "자동반영",
        "correctRate": 49.7
    },
    {
        "questionId": 9,
        "documentName": "연말정산시스템(YETA) 매뉴얼",
        "questionText": "수동 입력 항목 예시 한 가지를 작성하세요.",
        "difficulty": "NORMAL",
        "type": "SUBJECTIVE",
        "answer": "월세 세액공제",
        "tags": ["문제해결력"],
        "keyword": "수동 입력",
        "correctRate": 45.6
    },
    {
        "questionId": 10,
        "documentName": "연말정산시스템(YETA) 매뉴얼",
        "questionText": "제출 전 최종 검토 시 핵심 확인 사항은 무엇인가요?",
        "difficulty": "HARD",
        "type": "OBJECTIVE",
        "answer": "간소화자료와 입력 항목의 일치 여부",
        "tags": ["분석력"],
        "keyword": "최종 검토",
        "correctRate": 36.2
    },

    # 11~15: 연말정산 부양가족 공제 사례 매뉴얼 (신규 문서)
    {
        "questionId": 11,
        "documentName": "연말정산 부양가족 공제 사례 매뉴얼",
        "questionText": "부양가족 공제 대상이 아닌 경우는?",
        "difficulty": "EASY",
        "type": "OBJECTIVE",
        "answer": "연 소득 1,000만 원 초과 형제자매",
        "tags": ["이해력"],
        "keyword": "공제 요건",
        "correctRate": 60.3
    },
    {
        "questionId": 12,
        "documentName": "연말정산 부양가족 공제 사례 매뉴얼",
        "questionText": "부양가족 공제 시 중복 공제가 불가능한 사례는?",
        "difficulty": "NORMAL",
        "type": "OBJECTIVE",
        "answer": "형제와 부모가 동시에 같은 부양가족 공제를 신청",
        "tags": ["추론력"],
        "keyword": "중복 공제",
        "correctRate": 44.1
    },
    {
        "questionId": 13,
        "documentName": "연말정산 부양가족 공제 사례 매뉴얼",
        "questionText": "소득 조건 외에 공제 적용에 영향을 미치는 요소는?",
        "difficulty": "NORMAL",
        "type": "SUBJECTIVE",
        "answer": "실제 생계부양 여부",
        "tags": ["문제해결력"],
        "keyword": "부양요건",
        "correctRate": 40.0
    },
    {
        "questionId": 14,
        "documentName": "연말정산 부양가족 공제 사례 매뉴얼",
        "questionText": "부양가족 판단 시 연령 제한이 있는 항목은 무엇인가요?",
        "difficulty": "HARD",
        "type": "OBJECTIVE",
        "answer": "자녀 교육비 공제",
        "tags": ["분석력"],
        "keyword": "연령 기준",
        "correctRate": 35.8
    },
    {
        "questionId": 15,
        "documentName": "연말정산 부양가족 공제 사례 매뉴얼",
        "questionText": "소득이 있는 부양가족에 대해 공제 가능 여부를 작성하세요.",
        "difficulty": "HARD",
        "type": "SUBJECTIVE",
        "answer": "연 소득 100만 원 이하일 경우 가능",
        "tags": ["이해력"],
        "keyword": "소득 요건",
        "correctRate": 32.4
    }
]
