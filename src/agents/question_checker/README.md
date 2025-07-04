# Question Checker Agent

문제 생성 품질 검증 및 원본 문서 충실도 확인을 위한 도구들입니다.

## 📁 구조

```
question_checker/
├── __init__.py                           # 패키지 초기화
├── README.md                            # 사용법 가이드 
├── question_quality_checker.py         # 전체 문제 품질 평가 (LLM 기반)
├── question_quality_checker_simple.py  # 샘플 문제 품질 평가 (규칙 기반)  
├── document_fidelity_checker.py        # 원본 문서 충실도 검증
└── output/                             # 출력 결과 저장 디렉토리
    ├── question_quality_report_*.json
    ├── sample_question_quality_report_*.json
    └── document_fidelity_report_*.json
```

## 🛠️ 도구별 기능

### 1. Question Quality Checker (question_quality_checker.py)
**기능**: 생성된 모든 문제의 교육적 품질을 5가지 기준으로 평가
- 적절성 (Relevance)
- 난이도 적정성 (Appropriate Difficulty)  
- 명확성 및 모호성 없음 (Clarity and Unambiguity)
- 정답 및 해설의 정확성 (Correctness)
- 학습적 가치 및 유용성 (Educational Value)

**사용법**:
```bash
cd src/agents/question_checker
python question_quality_checker.py
```

### 2. Simple Question Quality Checker (question_quality_checker_simple.py)
**기능**: 샘플 문제들의 품질을 규칙 기반으로 빠르게 평가
- API 할당량 제한이 있을 때 사용
- 10개 샘플 문제만 평가
- 즉시 결과 확인 가능

**사용법**:
```bash
cd src/agents/question_checker  
python question_quality_checker_simple.py
```

### 3. Document Fidelity Checker (document_fidelity_checker.py)
**기능**: 생성된 문제가 원본 문서 내용과 일치하는지 검증
- 원본 문서 기반 여부
- 사실 정확성
- 맥락 일치성
- 용어 일관성
- 내용 추가/왜곡 여부

**사용법**:
```bash
cd src/agents/question_checker
python document_fidelity_checker.py
```

## 📊 출력 결과

모든 도구는 `output/` 디렉토리에 JSON 형태의 상세 보고서를 생성합니다:

- **평가 요약**: 전체 점수, 평균 점수, 평가 일시
- **기준별 점수**: 각 평가 기준별 세부 점수
- **문제별 결과**: 개별 문제의 상세 평가 결과
- **문제점 분석**: 발견된 문제점들의 요약

## 🔧 의존성

- `google.generativeai` - Gemini API 사용
- `python-dotenv` - 환경변수 로드
- `json`, `os`, `glob` - 파일 처리

## 💡 사용 팁

1. **API 제한**: Gemini API 할당량이 부족하면 Simple 버전 사용
2. **샘플 평가**: 빠른 확인을 위해서는 Simple 버전 권장
3. **원본 검증**: 문서 충실도 검증 전에 문서 분석 결과 필요
4. **결과 해석**: 3.5점 이상이면 양호, 4.0점 이상이면 우수한 품질

## 📈 평가 점수 기준

- **5점**: 매우 우수 (Excellent)
- **4점**: 우수 (Good) 
- **3점**: 보통 (Average)
- **2점**: 개선 필요 (Needs Improvement)
- **1점**: 부족 (Poor)