#!/usr/bin/env python3
"""
통합 문제 검증 도구
- 문제 품질 평가 (LLM 기반 / 규칙 기반)
- 문서 충실도 검증
- 통합 보고서 생성
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import glob
from langsmith import traceable

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# VectorDB 관련 import
try:
    from db.vectorDB.chromaDB.search import ChromaDBSearcher
    VECTOR_DB_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ VectorDB 모듈 로드 실패: {e}")
    print("📝 기본 충실도 검증 모드로 실행됩니다.")
    VECTOR_DB_AVAILABLE = False


class UnifiedQuestionChecker:
    """통합 문제 검증 클래스"""
    
    def __init__(self, use_vector_db: bool = True):
        # 실용적 품질 평가 기준 - 1~5점 척도
        self.quality_criteria = {
            "적절성": "문제가 학습 목표와 수준에 적합한지 - 5점: 매우 적절, 3점: 보통, 1점: 부적절",
            "난이도 적정성": "문제 난이도가 명시된 레벨에 적합한지 - 5점: 매우 적절, 3점: 보통, 1점: 부적절", 
            "명확성 및 모호성 없음": "문제와 선택지가 명확하고 모호하지 않은지 - 5점: 매우 명확, 3점: 보통, 1점: 모호함",
            "정답 및 해설의 정확성": "정답과 해설이 정확하고 논리적인지 - 5점: 완전 정확, 3점: 대체로 정확, 1점: 오류 있음",
            "학습적 가치 및 유용성": "교육적 효과와 실무 활용도가 높은지 - 5점: 매우 유용, 3점: 보통, 1점: 낮음"
        }
        
        self.fidelity_criteria = {
            "문서_충실도": "원본 문서와의 일치성 - 2점: 완전한 근거(직접 서술), 1점: 부분적 근거(추론 필요), 0점: 근거 없음(무관/모순)"
        }
        
        # VectorDB 초기화
        self.use_vector_db = use_vector_db and VECTOR_DB_AVAILABLE
        self.vector_searcher = None
        
        if self.use_vector_db:
            try:
                self.vector_searcher = ChromaDBSearcher()
                print("✅ VectorDB 검색 기능이 활성화되었습니다.")
            except Exception as e:
                print(f"⚠️ VectorDB 초기화 실패: {e}")
                self.use_vector_db = False
                print("📝 기본 충실도 검증 모드로 실행됩니다.")
        
        # LLM 프롬프트
        self.quality_prompt = """
다음 문제를 5가지 기준에 따라 객관적으로 평가해 주세요. 각 문제의 특성을 분석하여 차별화된 평가를 수행하세요.

[검증 기준]

1️⃣ **적절성 (1-5점)**
   문제가 학습 목표와 수준에 적합한지 평가하세요.
   - 5점: 학습 목표에 매우 적절하고 수준이 완벽히 맞음
   - 4점: 학습 목표에 적절하고 수준이 적당함
   - 3점: 보통 수준의 적절성
   - 2점: 일부 부적절한 요소가 있음
   - 1점: 학습 목표나 수준에 부적절함

2️⃣ **난이도 적정성 (1-5점)**
   문제 난이도가 명시된 레벨(EASY/MEDIUM/HARD)에 적합한지 평가하세요.
   - 5점: 난이도가 레벨에 매우 적절함
   - 4점: 난이도가 레벨에 적절함
   - 3점: 보통 수준의 난이도 적정성
   - 2점: 난이도가 레벨과 다소 맞지 않음
   - 1점: 난이도가 레벨과 전혀 맞지 않음

3️⃣ **명확성 및 모호성 없음 (1-5점)**
   문제와 선택지가 명확하고 모호하지 않은지 평가하세요.
   - 5점: 매우 명확하고 모호함이 전혀 없음
   - 4점: 명확하고 이해하기 쉬움
   - 3점: 보통 수준의 명확성
   - 2점: 일부 모호한 표현이 있음
   - 1점: 모호하거나 이해하기 어려움

4️⃣ **정답 및 해설의 정확성 (1-5점)**
   정답과 해설이 정확하고 논리적인지 평가하세요.
   - 5점: 정답과 해설이 완전히 정확하고 논리적임
   - 4점: 정답과 해설이 정확하고 적절함
   - 3점: 보통 수준의 정확성
   - 2점: 일부 부정확한 내용이 있음
   - 1점: 정답이나 해설에 명백한 오류가 있음

5️⃣ **학습적 가치 및 유용성 (1-5점)**
   교육적 효과와 실무 활용도가 높은지 평가하세요.
   - 5점: 매우 높은 교육적 효과와 실무 활용도
   - 4점: 높은 교육적 효과와 실무 활용도
   - 3점: 보통 수준의 학습적 가치
   - 2점: 교육적 효과가 다소 부족함
   - 1점: 교육적 효과나 실무 활용도가 낮음

[평가 지침]
- **다양한 점수 분포**: 5개 기준에서 다양한 점수(1-5점)를 활용하여 차별화된 평가 수행
- **구체적 근거 제시**: 각 점수에 대한 명확하고 구체적인 평가 근거 작성
- **객관적 평가**: 문제의 실제 특성을 바탕으로 주관적 편향 없이 평가
- **개선점 제시**: 부족한 부분에 대한 구체적인 개선 방향 제안

[총점 및 판정]
- 총점: 25점 만점 (각 기준 5점씩)
- 22-25점: 즉시 사용 가능 (Excellent)
- 18-21점: 검토 후 사용 (Good)
- 14-17점: 수정 후 사용 (Fair)
- 13점 이하: 재생성 필요 (Poor)

반드시 다음 JSON 형식으로만 응답해 주세요:
{
  "적절성": {
    "점수": [1-5 중 해당 점수],
    "평가사유": "[학습 목표와 수준 적합성에 대한 구체적 분석]"
  },
  "난이도 적정성": {
    "점수": [1-5 중 해당 점수],
    "평가사유": "[난이도와 레벨 일치성에 대한 구체적 평가]"
  },
  "명확성 및 모호성 없음": {
    "점수": [1-5 중 해당 점수],
    "평가사유": "[문제와 선택지의 명확성에 대한 구체적 분석]"
  },
  "정답 및 해설의 정확성": {
    "점수": [1-5 중 해당 점수],
    "평가사유": "[정답과 해설의 정확성에 대한 구체적 검증]"
  },
  "학습적 가치 및 유용성": {
    "점수": [1-5 중 해당 점수],
    "평가사유": "[교육적 효과와 실무 활용도에 대한 구체적 평가]"
  },
  "Quality Score": [5개 기준 점수의 합계],
  "Quality Score 최대": 25,
  "품질등급": "[Excellent/Good/Fair/Poor 중 해당 등급]",
  "종합평가": "[전체적인 평가 요약과 개선 방향 제시]"
}

**중요**: 각 문제의 고유한 특성을 반영하여 다양한 점수 분포로 차별화된 평가를 수행하세요.
"""

        self.fidelity_prompt = """
제시된 문제가 원본 문서 내용을 정확하게 반영하고 있는지 "Attributed Question Answering" 논문 기준에 따라 검증해 주세요.

[검증 원칙]
1. **구체적 비교**: 문제의 모든 요소를 원본 문서의 구체적 부분과 직접 비교
2. **상세한 근거**: 점수 판단의 근거를 원본 문서의 구체적 내용 인용으로 제시
3. **차이점 명시**: 원본과 다른 부분이 있다면 정확히 무엇이 다른지 구체적으로 지적
4. **이미지 정보**: 이미지 기반 문제는 이미지 설명과 추출된 데이터를 세밀하게 검증
5. **교육적 관점**: 원본 충실도와 더불어 교육적 효과도 함께 고려

[검증 기준]

🟢 2점 (완전한 근거)
✅ 답변 내용이 출처에 직접적으로 서술됨
✅ 문장의 표현만 다르고 사실관계/정보가 완전히 일치
✅ 출처만 보고도 그 답을 재구성할 수 있음
✅ 논리적 추론이 거의 필요 없음

예시
출처: "공룡은 약 2억 3천만 년 전에 처음 출현했다."
질문: "공룡은 언제 등장했나요?"
답변: "공룡은 약 2억 3천만 년 전에 등장했습니다."
→ 2점 (정보 그대로)

🟡 1점 (부분적 근거)
✅ 출처에 부분 정보 또는 단서가 존재함
✅ 답변이 출처에 있는 정보에 추론·해석·확장을 더해 작성됨
✅ 출처에 "힌트"는 있지만, 답변을 100% 재구성하기는 어려움
✅ 정보의 일부는 출처에 없거나, 출처에 명확히 나타나지 않음

예시
출처: "공룡은 중생대 트라이아스기에 출현했다."
질문: "공룡은 언제 등장했나요?"
답변: "공룡은 약 2억 3천만 년 전에 등장했습니다."
→ 1점 (트라이아스기 = 약 2억 3천만 년 전이라는 추론이 필요)

또는:
출처: "공룡은 육식과 초식이 모두 존재했다."
질문: "공룡은 무엇을 먹었나요?"
답변: "공룡은 육식성 종류도 있었고 초식성 종류도 있었습니다."
→ 1점 (출처에 요약 단서 있지만 세부 정보는 일부 확장됨)

🔴 0점 (근거 없음)
✅ 출처에 관련 정보가 전혀 없음
✅ 출처 내용과 답변이 모순되거나 충돌
✅ 답변이 전적으로 외부 정보에 기반하거나 추측적임

예시
출처: "공룡은 약 2억 년 전에 출현했다."
질문: "공룡은 어디에서 등장했나요?"
답변: "공룡은 북아메리카에서 처음 나타났습니다."
→ 0점 (출처에 장소 정보 없음)

또는:
출처: "공룡은 초식성이었다."
질문: "공룡은 무엇을 먹었나요?"
답변: "공룡은 육식성이었다."
→ 0점 (출처와 모순)

📝 판단 프로세스 가이드
판단할 때 아래 단계로 검토하면 좋습니다:

1️⃣ 출처에 답변 정보가 직접적으로 서술되어 있는지 확인
2️⃣ 만약 직접 서술되지 않았다면, 출처의 정보에서 합리적 추론이 가능한지 평가
3️⃣ 정보의 일부만 출처에 있거나, 다소 모호하면 부분적 근거
4️⃣ 출처에 관련 정보가 없거나 모순되면 근거 없음


**중요**: 각 문제별로 원본 문서와의 실제 비교를 통해 차별화된 검증 결과를 제시하세요.

반드시 다음 JSON 형식으로만 응답해 주세요:
{
  "문서_충실도": {
    "점수": [0, 1, 2 중 해당 점수],
    "검증사유": "[원본 문서와의 비교 분석 및 판단 근거]",
    "문제점": "[발견된 문제점이나 개선사항]"
  },
  "종합검증": "[전체적인 충실도 평가 요약 및 개선 방향]"
}
"""

    # ========================================================================
    # 1. 문제 로딩 관련 메서드들
    # ========================================================================
    
    def load_questions_from_files(self, directory_path: str, max_questions: int = None) -> List[Dict]:
        """generated_questions 디렉토리에서 문제들을 로드"""
        questions = []
        
        # basic_questions 파일들 로드
        basic_files = glob.glob(os.path.join(directory_path, "basic_questions_*.json"))
        for file_path in basic_files:
            questions.extend(self._load_questions_from_file(file_path, 'basic', max_questions))
        
        # extra_questions 파일들 로드  
        extra_files = glob.glob(os.path.join(directory_path, "extra_questions_*.json"))
        for file_path in extra_files:
            questions.extend(self._load_questions_from_file(file_path, 'extra', max_questions))
            
        return questions[:max_questions] if max_questions else questions
    
    def load_questions_from_file(self, file_path: str) -> List[Dict]:
        """단일 파일에서 문제들을 로드"""
        file_type = 'basic' if 'basic_questions' in file_path else 'extra'
        return self._load_questions_from_file(file_path, file_type)
    
    def load_sample_questions(self, directory_path: str, max_questions: int = 10) -> List[Dict]:
        """최신 파일에서 샘플 문제들만 로드"""
        questions = []
        
        # 최신 basic_questions 파일 1개만 로드
        basic_files = sorted(glob.glob(os.path.join(directory_path, "basic_questions_*.json")), reverse=True)
        if basic_files:
            file_path = basic_files[0]
            questions = self._load_questions_from_file(file_path, 'basic', max_questions)
                
        return questions
    
    def _load_questions_from_file(self, file_path: str, file_type: str, max_questions: int = None) -> List[Dict]:
        """단일 파일에서 문제들 로드"""
        questions = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                count = 0
                # 새로운 구조: questions_by_document
                if isinstance(data, dict) and 'questions_by_document' in data:
                    for doc_name, doc_questions in data['questions_by_document'].items():
                        for q in doc_questions:
                            if max_questions and count >= max_questions:
                                break
                            q['file_type'] = file_type
                            q['source_file'] = os.path.basename(file_path)
                            q['document_name'] = doc_name
                            questions.append(q)
                            count += 1
                        if max_questions and count >= max_questions:
                            break
                # 기존 구조: questions 배열
                elif isinstance(data, dict) and 'questions' in data:
                    for q in data['questions']:
                        if max_questions and count >= max_questions:
                            break
                        q['file_type'] = file_type
                        q['source_file'] = os.path.basename(file_path)
                        questions.append(q)
                        count += 1
                # 직접 배열
                elif isinstance(data, list):
                    for q in data:
                        if max_questions and count >= max_questions:
                            break
                        q['file_type'] = file_type
                        q['source_file'] = os.path.basename(file_path)
                        questions.append(q)
                        count += 1
        except Exception as e:
            print(f"⚠️ 파일 로드 실패 ({file_path}): {e}")
        
        return questions


    # ========================================================================
    # 2. 문제 품질 평가 관련 메서드들 (LLM 기반)
    # ========================================================================
    
    @traceable(
        run_type="chain",
        name="Evaluate Question Quality",
        metadata={"agent_type": "question_checker"}
    )
    def evaluate_question_quality_llm(self, question: Dict) -> Dict:
        """OpenAI를 사용하여 문제 품질 평가 (gpt-3.5-turbo, openai>=1.0.0)"""
        try:
            import openai
            from openai import OpenAI
            from langsmith.wrappers import wrap_openai
            from dotenv import load_dotenv
            load_dotenv(override=True)
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if not openai_api_key:
                return self._get_default_quality_evaluation()
            client = wrap_openai(OpenAI(api_key=openai_api_key))
            question_text = self._format_question_for_evaluation(question)
            prompt = f"{self.quality_prompt}\n\n평가할 문제:\n{question_text}"
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "당신은 문제 품질 평가 전문가입니다. 반드시 JSON만 반환하세요."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            response_text = response.choices[0].message.content.strip()
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```", 1)[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```", 1)[1].split("```", 1)[0].strip()
            evaluation = json.loads(response_text)
            return evaluation
        except Exception as e:
            print(f"⚠️ OpenAI 품질 평가 실패: {e}")
            return self._get_default_quality_evaluation()

    # ========================================================================
    # 3. 문서 충실도 검증 관련 메서드들
    # ========================================================================
    
    def _is_image_based_question(self, question: Dict) -> bool:
        """문제가 이미지 기반인지 확인"""
        question_text = question.get('question', '').lower()
        explanation = question.get('explanation', '').lower()
        
        # 이미지 관련 키워드 확인
        image_keywords = [
            '그림', '도표', '차트', '다이어그램', '플로우차트', '순서도', '구조도',
            '이미지', '사진', '그래프', '표', '도면', '스크린샷', '화면',
            '위 그림', '아래 그림', '다음 그림', '위 도표', '아래 도표'
        ]
        
        text_to_check = f"{question_text} {explanation}"
        return any(keyword in text_to_check for keyword in image_keywords)
    
    @traceable(
        run_type="chain",
        name="Evaluate Document Fidelity",
        metadata={"agent_type": "question_checker"}
    )
    def evaluate_document_fidelity_llm(self, question: Dict, source_documents: Dict[str, Dict]) -> Dict:
        """OpenAI를 사용하여 문서 충실도 검증 (VectorDB 또는 파일 기반)"""
        try:
            import openai
            from openai import OpenAI
            from langsmith.wrappers import wrap_openai
            from dotenv import load_dotenv
            load_dotenv(override=True)
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if not openai_api_key:
                return self._get_default_fidelity_evaluation()
            client = wrap_openai(OpenAI(api_key=openai_api_key))
            
            # VectorDB 검색만 사용
            document_content = ""
            if self.use_vector_db and self.vector_searcher:
                try:
                    question_text = question.get('question', '')
                    # 사용 가능한 컬렉션 찾기
                    collections = self.vector_searcher.client.get_client().list_collections()
                    if collections:
                        collection_name = collections[0].name
                        search_results = self.vector_searcher.search_similar(
                            query=question_text,
                            collection_name=collection_name,
                            n_results=3
                        )
                        if search_results and len(search_results) > 0:
                            document_content = ' '.join([result.get('content', '') for result in search_results])
                            print(f"📝 VectorDB에서 관련 문서 검색 완료: {len(search_results)}개 결과")
                        else:
                            print("⚠️ VectorDB 검색 결과 없음")
                    else:
                        print("⚠️ 사용 가능한 컬렉션이 없음")
                except Exception as e:
                    print(f"⚠️ VectorDB 검색 실패: {e}")
            else:
                print("⚠️ VectorDB를 사용할 수 없음")
                
            if not document_content:
                print("⚠️ VectorDB에서 비교할 문서 내용을 찾을 수 없음")
                return self._get_default_fidelity_evaluation()
                
            question_text = self._format_question_for_evaluation(question)
            
            # 이미지 기반 문제인지 확인
            is_image_based = self._is_image_based_question(question)
            image_note = ""
            if is_image_based:
                image_note = "\n\n**주의: 이 문제는 이미지 기반 문제입니다. 이미지 정보와 문제 내용의 일치성을 특별히 검증해주세요.**"
            
            prompt = f"{self.fidelity_prompt}\n\n원본 문서 내용:\n{document_content[:2000]}...\n\n검증할 문제:\n{question_text}{image_note}"
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "당신은 문서 충실도 검증 전문가입니다. 반드시 JSON만 반환하세요."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1500
            )
            response_text = response.choices[0].message.content.strip()
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```", 1)[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```", 1)[1].split("```", 1)[0].strip()
            evaluation = json.loads(response_text)
            return evaluation
        except Exception as e:
            print(f"⚠️ OpenAI 충실도 검증 실패: {e}")
            return self._get_default_fidelity_evaluation()


    # ========================================================================
    # 4. 통합 보고서 생성 메서드들
    # ========================================================================
    
    def generate_comprehensive_report(self, questions: List[Dict], check_fidelity: bool = True, 
                                    output_file: str = None) -> Dict:
        """종합 보고서 생성"""
        print(f"🔍 {len(questions)}개 문제 종합 검증 시작...")
        
        # VectorDB만 사용하므로 별도 문서 로딩 불필요
        
        evaluations = []
        quality_totals = {criterion: 0 for criterion in self.quality_criteria.keys()}
        fidelity_totals = {criterion: 0 for criterion in self.fidelity_criteria.keys()}
        
        for i, question in enumerate(questions, 1):
            print(f"  📝 문제 {i}/{len(questions)} 검증 중...")
            
            # 1. 품질 평가 (LLM 기반)
            quality_eval = self.evaluate_question_quality_llm(question)
            
            # 2. 충실도 검증 (VectorDB 기반)
            fidelity_eval = {}
            if check_fidelity:
                fidelity_eval = self.evaluate_document_fidelity_llm(question, {})
            
            # 결과 통합
            evaluation = {
                'question_id': i,
                'question_info': {
                    'type': question.get('type'),
                    'difficulty_level': question.get('difficulty_level'),
                    'tags': question.get('tags', []),
                    'source_file': question.get('source_file'),
                    'document_name': question.get('document_name'),
                    'question': question.get('question', '')[:100] + '...' if len(question.get('question', '')) > 100 else question.get('question', '')
                },
                'quality_evaluation': quality_eval,
                'fidelity_evaluation': fidelity_eval if check_fidelity else {}
            }
            
            evaluations.append(evaluation)
            
            # 점수 집계
            for criterion in self.quality_criteria.keys():
                if criterion in quality_eval and '점수' in quality_eval[criterion]:
                    quality_totals[criterion] += quality_eval[criterion]['점수']
            
            if check_fidelity:
                for criterion in self.fidelity_criteria.keys():
                    if criterion in fidelity_eval and '점수' in fidelity_eval[criterion]:
                        fidelity_totals[criterion] += fidelity_eval[criterion]['점수']
        
        # 평균 점수 계산
        quality_averages = {criterion: round(score / len(questions), 2) for criterion, score in quality_totals.items()}
        fidelity_averages = {criterion: round(score / len(questions), 2) for criterion, score in fidelity_totals.items()} if check_fidelity else {}
        
        # Quality Score 계산 (5점 척도 기준)
        total_quality_score = 0
        quality_score_count = 0
        for evaluation in evaluations:
            quality_eval = evaluation['quality_evaluation']
            if 'Quality Score' in quality_eval:
                total_quality_score += quality_eval['Quality Score']
                quality_score_count += 1
        
        average_quality_score = round(total_quality_score / quality_score_count, 2) if quality_score_count > 0 else 0
        
        # 보고서 생성
        report = {
            "검증_요약": {
                "총_문제수": len(questions),
                "검증_일시": datetime.now().isoformat(),
                "검증_방식": "5점_척도_품질평가",
                "품질_평가_평균": quality_averages,
                "Quality_Score_평균": average_quality_score,
                "Quality_Score_최대": 25,
                "품질등급": "Excellent" if average_quality_score >= 22 else "Good" if average_quality_score >= 18 else "Fair" if average_quality_score >= 14 else "Poor",
                "충실도_검증_평균": fidelity_averages,
                "충실도_전체_평균": round(sum(fidelity_averages.values()) / len(fidelity_averages), 2) if fidelity_averages else 0,
                "충실도_최대점수": 2
            },
            "검증_기준": {
                "품질_평가_기준": self.quality_criteria,
                "충실도_검증_기준": self.fidelity_criteria if check_fidelity else {}
            },
            "문제별_검증결과": evaluations
        }
        
        # 파일 저장
        if not output_file:
            output_file = f"output/comprehensive_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 5점 척도 기반 종합 검증 완료! 보고서 저장: {output_file}")
        print(f"📊 Quality Score 평균: {average_quality_score}/25.0 ({report['검증_요약']['품질등급']})")
        if check_fidelity:
            print(f"📋 충실도 검증 평균: {report['검증_요약']['충실도_전체_평균']}/2.0")
        
        return report

    # ========================================================================
    # 5. 유틸리티 메서드들
    # ========================================================================
    
    def _format_question_for_evaluation(self, question: Dict) -> str:
        """문제를 평가용 텍스트로 포맷팅"""
        formatted = f"=== 문제 ===\n{question.get('question', '')}\n"
        
        if question.get('type') == 'OBJECTIVE':
            formatted += f"\n=== 선택지 ===\n"
            for i, option in enumerate(question.get('options', []), 1):
                formatted += f"{i}. {option}\n"
            formatted += f"\n정답: {question.get('answer', '')}"
        else:
            formatted += f"\n=== 예시 답안 ===\n{question.get('answer', '')}"
            
        if question.get('explanation'):
            formatted += f"\n\n=== 해설 ===\n{question.get('explanation', '')}"
            
        return formatted


    def _get_default_quality_evaluation(self) -> Dict:
        """기본 품질 평가 (LLM 사용 불가 시) - 5점 척도 기준"""
        return {
            "적절성": {"점수": 3, "평가사유": "자동 평가 불가 - 학습 목표 적합성 추정"},
            "난이도 적정성": {"점수": 3, "평가사유": "자동 평가 불가 - 난이도 레벨 적정성 추정"},
            "명확성 및 모호성 없음": {"점수": 3, "평가사유": "자동 평가 불가 - 명확성 추정"},
            "정답 및 해설의 정확성": {"점수": 3, "평가사유": "자동 평가 불가 - 정확성 추정"},
            "학습적 가치 및 유용성": {"점수": 3, "평가사유": "자동 평가 불가 - 교육적 가치 추정"},
            "Quality Score": 15,
            "Quality Score 최대": 25,
            "품질등급": "Fair",
            "종합평가": "자동 평가를 사용할 수 없어 수동 검토가 필요합니다. 15/25점으로 수정 후 사용 권장."
        }

    def _get_default_fidelity_evaluation(self) -> Dict:
        """기본 충실도 평가 (LLM 사용 불가 시) - Attributed QA 기준"""
        return {
            "문서_충실도": {"점수": 1, "검증사유": "자동 검증 불가 - 원본 문서와의 직접 비교가 필요함", "문제점": "수동 확인 필요"},
            "종합검증": "자동 검증을 사용할 수 없어 수동 검토가 필요합니다. 원본 문서와의 직접 비교를 통해 충실도를 평가해주세요."
        }

    def print_statistics(self, questions: List[Dict]):
        """문제 통계 출력"""
        type_counts = {}
        difficulty_counts = {}
        tag_counts = {}
        
        for q in questions:
            q_type = q.get('type', 'UNKNOWN')
            difficulty = q.get('difficulty_level', 'UNKNOWN')
            tags = q.get('tags', [])
            
            type_counts[q_type] = type_counts.get(q_type, 0) + 1
            difficulty_counts[difficulty] = difficulty_counts.get(difficulty, 0) + 1
            
            for tag in tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        print(f"📊 문제 유형별: {type_counts}")
        print(f"📊 난이도별: {difficulty_counts}")
        print(f"📊 태그별: {dict(sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:5])}")


def main():
    """메인 실행 함수"""
    print("🎯 통합 문제 검증 도구 (LLM 기반)")
    print("=" * 80)
    
    # 명령행 인자 처리
    if len(sys.argv) > 1:
        # 특정 파일이 지정된 경우
        questions_file = sys.argv[1]
        if not os.path.exists(questions_file):
            print(f"❌ 파일을 찾을 수 없습니다: {questions_file}")
            return
        
        # UnifiedQuestionChecker 초기화
        checker = UnifiedQuestionChecker()
        
        # 파일에서 문제 로드
        questions = checker.load_questions_from_file(questions_file)
        if questions:
            checker.print_statistics(questions)
            report = checker.generate_comprehensive_report(
                questions, check_fidelity=True,
                output_file=f"output/llm_file_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
        else:
            print("❌ 평가할 문제를 찾을 수 없습니다.")
        return
    
    # 경로 설정
    questions_dir = "../../../data/outputs/generated_questions"
    
    # UnifiedQuestionChecker 초기화
    checker = UnifiedQuestionChecker()
    
    # 사용자 선택
    print("\n검증 모드를 선택하세요:")
    print("1. 샘플 검증 (10개, 빠름)")
    print("2. 전체 검증 (모든 문제, 느림)")
    print("3. 충실도 검증 없이 품질만 평가")
    
    choice = input("선택 (1-3): ").strip()
    
    if choice == "1":
        # 샘플 검증 (LLM 사용)
        questions = checker.load_sample_questions(questions_dir, 10)
        if questions:
            checker.print_statistics(questions)
            report = checker.generate_comprehensive_report(
                questions, check_fidelity=True,
                output_file=f"output/llm_sample_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
        else:
            print("❌ 평가할 문제를 찾을 수 없습니다.")
    
    elif choice == "2":
        # 전체 검증 (LLM 사용)
        questions = checker.load_questions_from_files(questions_dir)
        if questions:
            checker.print_statistics(questions)
            report = checker.generate_comprehensive_report(
                questions, check_fidelity=True,
                output_file=f"output/llm_full_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
        else:
            print("❌ 평가할 문제를 찾을 수 없습니다.")
    
    elif choice == "3":
        # 품질 평가만 (충실도 검증 없음)
        questions = checker.load_sample_questions(questions_dir, 10)
        if questions:
            checker.print_statistics(questions)
            report = checker.generate_comprehensive_report(
                questions, check_fidelity=False,
                output_file=f"output/llm_quality_only_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
        else:
            print("❌ 평가할 문제를 찾을 수 없습니다.")
    
    else:
        print("❌ 잘못된 선택입니다.")

if __name__ == "__main__":
    main()