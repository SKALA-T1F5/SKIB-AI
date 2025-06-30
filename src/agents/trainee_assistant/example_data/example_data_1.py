example_inputs = [
    {
        "userQuestion": "정답이 Docker인 이유를 다시 설명해주세요.",
        "questionInfo": {
            "questionId": "3",
            "type": "OBJECTIVE",
            "question": "다음 중 프론트엔드 빌드 도구가 아닌 것은?",
            "options": ["Webpack", "Parcel", "Docker", "Vite"],
            "explanation": "Docker는 컨테이너 도구로, 프론트엔드 빌드 도구가 아닙니다.",
            "response": "Parcel",
            "answer": "Docker",
            "score": 0,
            "isCorrect": False,
            "gradingCriteria": []
        },
        "messageHistory": [
            { "role": "user", "content": "왜 이 문제가 틀렸는지 모르겠어요." },
            { "role": "assistant", "content": "이 문제는 '다음 중 프론트엔드 빌드 도구가 아닌 것은?'입니다. Docker는 프론트엔드와는 관계없는 컨테이너 도구이기 때문에 정답입니다." }
        ]
    },
    {
        "userQuestion": "Tailwind가 정답인 이유를 알려주세요.",
        "questionInfo": {
            "questionId": "12",
            "type": "OBJECTIVE",
            "question": "다음 중 유틸리티 기반 CSS 프레임워크는 무엇인가요?",
            "options": ["Bootstrap", "Foundation", "Tailwind", "Bulma"],
            "explanation": "Tailwind는 유틸리티 클래스 기반으로 스타일을 구성하는 프레임워크입니다.",
            "response": "Tailwind",
            "answer": "Tailwind",
            "score": 1,
            "isCorrect": True,
            "gradingCriteria": []
        },
        "messageHistory": [
            { "role": "user", "content": "이 문제 맞았는데, 그래도 해설 부탁드려요." },
            { "role": "assistant", "content": "Tailwind는 다른 CSS 프레임워크와 달리 유틸리티 클래스 중심으로 스타일을 만듭니다." }
        ]
    },
    {
        "userQuestion": "제 답변이 왜 틀렸는지 자세히 알려주세요.",
        "questionInfo": {
            "questionId": "21",
            "type": "SUBJECTIVE",
            "question": "RESTful API의 핵심 원칙 두 가지를 설명하세요.",
            "options": [],
            "explanation": "REST의 핵심 원칙에는 자원 기반 URI 설계와 무상태성(stateless)이 포함됩니다.",
            "response": "REST는 빠르게 동작해야 하고, 데이터를 암호화해야 합니다.",
            "answer": "자원 기반 설계, 무상태성",
            "score": 1,
            "isCorrect": False,
            "gradingCriteria": [
                {
                    "score": 0,
                    "criteria": "관련 없는 설명",
                    "example": ".",
                    "note": "REST 원칙과 관련 없는 기술적 요소 언급"
                },
                {
                    "score": 1,
                    "criteria": "REST 개념을 혼동하여 서술",
                    "example": "REST는 빠른 응답을 위한 방식입니다",
                    "note": "핵심 원칙이 빠진 설명"
                }
            ]
        },
        "messageHistory": [
            { "role": "user", "content": "REST 원칙에 대해 적었는데 왜 틀렸을까요?" },
            { "role": "assistant", "content": "답변에서 핵심 원칙인 '자원 기반 설계'와 '무상태성'이 빠져 있습니다." }
        ]
    },
    {
        "userQuestion": "모듈 번들러에 대해 더 자세히 설명해주세요.",
        "questionInfo": {
            "questionId": "5",
            "type": "OBJECTIVE",
            "question": "다음 중 모듈 번들러로 사용되는 도구는 무엇인가요?",
            "options": ["Webpack", "Jest", "ESLint", "Prettier"],
            "explanation": "Webpack은 자바스크립트 모듈을 하나의 파일로 번들링해주는 도구입니다.",
            "response": "Webpack",
            "answer": "Webpack",
            "score": 1,
            "isCorrect": True,
            "gradingCriteria": []
        },
        "messageHistory": [
            { "role": "user", "content": "Webpack이 정답인데 정확히 어떤 역할을 하나요?" }
        ]
    },
    {
        "userQuestion": "이 답변이 왜 만점인 건가요?",
        "questionInfo": {
            "questionId": "30",
            "type": "SUBJECTIVE",
            "question": "CSR(Client Side Rendering)과 SSR(Server Side Rendering)의 차이를 설명하세요.",
            "options": [],
            "explanation": "CSR은 브라우저에서 렌더링되고, SSR은 서버에서 HTML을 생성하여 전달합니다.",
            "response": "CSR은 브라우저에서 렌더링되고, SSR은 서버에서 렌더링되어 초기 로딩이 빠릅니다.",
            "answer": "CSR은 클라이언트 렌더링, SSR은 서버 렌더링",
            "score": 5,
            "isCorrect": True,
            "gradingCriteria": [
                {
                    "score": 5,
                    "criteria": "CSR/SSR의 차이점을 구체적으로 비교 설명",
                    "example": "CSR은 브라우저에서, SSR은 서버에서 렌더링한다",
                    "note": "정확하고 핵심 요소를 모두 포함"
                }
            ]
        },
        "messageHistory": [
            { "role": "user", "content": "제 설명이 왜 만점이 나왔나요?" },
            { "role": "assistant", "content": "CSR과 SSR의 핵심 차이점을 잘 설명했기 때문에 만점입니다." }
        ]
    }
]
