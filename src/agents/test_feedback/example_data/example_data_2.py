# agents/test_feedback/example_data/example_data_2.py
# 클라우드 기반 데이터베이스 관리 역량 평가 시험 (보안 문서 정답률 낮음)

# 시험 목표 2
exam_goal = '클라우드 기반 데이터베이스 관리 역량을 평가하는 시험입니다. 관계형 및 NoSQL 데이터베이스의 기본 개념, 확장성, 보안 전략을 중심으로 객관식 및 실습형으로 생성하겠습니다.'

# 문항별 응시 결과 2 
question_results = [
    # 1~5: AWS RDS 가이드
    {
        "questionId": 1,
        "documentName": "AWS RDS 가이드",
        "questionText": "AWS RDS에서 지원하는 관계형 데이터베이스 엔진 중 하나는 무엇인가요?",
        "difficulty": "EASY",
        "type": "OBJECTIVE",
        "answer": "MySQL",
        "tags": ["기초이해"],
        "keyword": "관계형 DB",
        "correctRate": 92.10
    },
    {
        "questionId": 2,
        "documentName": "AWS RDS 가이드",
        "questionText": "RDS 인스턴스 백업을 위한 기능은 무엇인가요?",
        "difficulty": "NORMAL",
        "type": "OBJECTIVE",
        "answer": "스냅샷",
        "tags": ["문제해결력"],
        "keyword": "DB 백업",
        "correctRate": 78.55
    },
    {
        "questionId": 3,
        "documentName": "AWS RDS 가이드",
        "questionText": "RDS 다중 AZ 배포의 목적을 설명하세요.",
        "difficulty": "HARD",
        "type": "SUBJECTIVE",
        "answer": "고가용성 확보",
        "tags": ["분석력"],
        "keyword": "다중 AZ",
        "correctRate": 55.20
    },
    {
        "questionId": 4,
        "documentName": "AWS RDS 가이드",
        "questionText": "RDS의 자동 장애 조치 기능은 어떤 구성에서 가능한가요?",
        "difficulty": "HARD",
        "type": "OBJECTIVE",
        "answer": "다중 AZ",
        "tags": ["추론력"],
        "keyword": "장애 조치",
        "correctRate": 47.30
    },
    {
        "questionId": 5,
        "documentName": "AWS RDS 가이드",
        "questionText": "RDS 인스턴스 크기를 조정할 수 있는 기능은 무엇인가요?",
        "difficulty": "NORMAL",
        "type": "OBJECTIVE",
        "answer": "스케일링",
        "tags": ["이해력"],
        "keyword": "성능 조정",
        "correctRate": 69.20
    },

    # 6~10: MongoDB Atlas Documentation
    {
        "questionId": 6,
        "documentName": "MongoDB Atlas Documentation",
        "questionText": "NoSQL 데이터베이스의 특징 중 하나는 무엇인가요?",
        "difficulty": "EASY",
        "type": "OBJECTIVE",
        "answer": "스키마리스",
        "tags": ["기초이해"],
        "keyword": "NoSQL 특징",
        "correctRate": 85.00
    },
    {
        "questionId": 7,
        "documentName": "MongoDB Atlas Documentation",
        "questionText": "MongoDB에서 데이터를 그룹화하여 저장하는 단위는 무엇인가요?",
        "difficulty": "NORMAL",
        "type": "OBJECTIVE",
        "answer": "컬렉션",
        "tags": ["이해력"],
        "keyword": "MongoDB",
        "correctRate": 68.90
    },
    {
        "questionId": 8,
        "documentName": "MongoDB Atlas Documentation",
        "questionText": "샤딩(Sharding)의 주요 목적을 설명하세요.",
        "difficulty": "HARD",
        "type": "SUBJECTIVE",
        "answer": "수평 확장",
        "tags": ["추론력"],
        "keyword": "샤딩",
        "correctRate": 48.70
    },
    {
        "questionId": 9,
        "documentName": "MongoDB Atlas Documentation",
        "questionText": "MongoDB에서 하나의 문서가 저장될 수 있는 최대 크기는?",
        "difficulty": "NORMAL",
        "type": "OBJECTIVE",
        "answer": "16MB",
        "tags": ["기초이해"],
        "keyword": "문서 크기",
        "correctRate": 59.50
    },
    {
        "questionId": 10,
        "documentName": "MongoDB Atlas Documentation",
        "questionText": "MongoDB에서 복제(replication)의 목적은 무엇인가요?",
        "difficulty": "EASY",
        "type": "SUBJECTIVE",
        "answer": "데이터 가용성 확보",
        "tags": ["논리력"],
        "keyword": "복제",
        "correctRate": 87.10
    },

    # 11~15: 데이터베이스 보안 모범 사례 (정답률 하향)
    {
        "questionId": 11,
        "documentName": "데이터베이스 보안 모범 사례",
        "questionText": "데이터베이스 접근 제어 시 필수적인 보안 원칙은 무엇인가요?",
        "difficulty": "EASY",
        "type": "OBJECTIVE",
        "answer": "최소 권한",
        "tags": ["문제해결력"],
        "keyword": "접근 제어",
        "correctRate": 41.30
    },
    {
        "questionId": 12,
        "documentName": "데이터베이스 보안 모범 사례",
        "questionText": "데이터베이스 암호화 시 고려할 사항 한 가지를 작성하세요.",
        "difficulty": "NORMAL",
        "type": "SUBJECTIVE",
        "answer": "키 관리",
        "tags": ["논리력"],
        "keyword": "DB 암호화",
        "correctRate": 38.80
    },
    {
        "questionId": 13,
        "documentName": "데이터베이스 보안 모범 사례",
        "questionText": "SQL Injection 방지를 위한 방법 한 가지를 설명하세요.",
        "difficulty": "HARD",
        "type": "SUBJECTIVE",
        "answer": "Prepared Statement 사용",
        "tags": ["분석력"],
        "keyword": "SQL Injection",
        "correctRate": 33.25
    },
    {
        "questionId": 14,
        "documentName": "데이터베이스 보안 모범 사례",
        "questionText": "DB 접근 로그를 주기적으로 점검해야 하는 이유는 무엇인가요?",
        "difficulty": "NORMAL",
        "type": "SUBJECTIVE",
        "answer": "비정상 접근 탐지",
        "tags": ["문제해결력"],
        "keyword": "로그 점검",
        "correctRate": 36.10
    },
    {
        "questionId": 15,
        "documentName": "데이터베이스 보안 모범 사례",
        "questionText": "암호화 키를 안전하게 저장하기 위한 방법은 무엇인가요?",
        "difficulty": "EASY",
        "type": "OBJECTIVE",
        "answer": "HSM",
        "tags": ["기초이해"],
        "keyword": "키 보관",
        "correctRate": 44.00
    }
]

