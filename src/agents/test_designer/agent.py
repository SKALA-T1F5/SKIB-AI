"""
테스트 설계 Agent (Simple 패턴)
- 키워드와 문서 요약을 분석
- 사용자 프롬프트를 GPT-4에 전달
- 테스트 요약 및 config 생성
"""

import os
import json
import time
from typing import Dict, Any, List
from datetime import datetime
import openai
from openai import OpenAI
from dotenv import load_dotenv
from .tools.requirement_analyzer import RequirementAnalyzer
from .tools.test_config_generator import TestConfigGenerator

# 환경 변수 로드
load_dotenv(override=True)
api_key = os.getenv("OPENAI_API_KEY")
openai_client = OpenAI(api_key=api_key)


class TestDesignerAgent:
    """
    테스트 설계 전문 Agent (Simple 패턴)
    
    주요 기능:
    - 사용자 요구사항 분석
    - GPT-4를 활용한 테스트 요약 생성
    - 테스트 설정 및 구성 생성
    - 문제 수와 난이도 자동 결정
    """
    
    def __init__(self):
        """
        TestDesigner 초기화
        """
        self.requirement_analyzer = RequirementAnalyzer()
        self.config_generator = TestConfigGenerator()
    
    def design_test(
        self,
        keywords: List[str],
        document_summary: str,
        document_topics: List[str],
        user_prompt: str,
        difficulty: str = "medium",
        test_type: str = "mixed",
        time_limit: int = 60
    ) -> Dict[str, Any]:
        """
        테스트 설계 실행
        
        Args:
            keywords: 문서 키워드 목록
            document_summary: 문서 요약
            document_topics: 주요 주제 목록
            user_prompt: 사용자 요청 프롬프트
            difficulty: 난이도 (easy, medium, hard)
            test_type: 테스트 유형 (objective, subjective, mixed)
            time_limit: 제한시간 (분)
            
        Returns:
            Dict: 테스트 설계 결과
        """
        start_time = time.time()
        
        print("🎯 TestDesignerAgent 시작")
        print(f"📝 사용자 요청: {user_prompt}")
        print(f"🔑 키워드: {len(keywords)}개")
        print(f"📋 주제: {len(document_topics)}개")
        print(f"⚡ 난이도: {difficulty}")
        
        try:
            # 1. 요구사항 분석
            print("\n🔄 1단계: 요구사항 분석")
            requirements = self._analyze_requirements(
                keywords, document_summary, document_topics, user_prompt, difficulty, test_type, time_limit
            )
            
            # 2. 테스트 요약 생성
            print("\n🔄 2단계: 테스트 요약 생성")
            test_summary = self._generate_test_summary(requirements)
            
            # 3. 테스트 config 생성
            print("\n🔄 3단계: 테스트 설정 생성")
            test_config = self._create_test_config(test_summary, requirements)
            
            # 처리 시간 계산
            processing_time = time.time() - start_time
            
            # 결과 구성
            result = {
                "test_summary": test_summary,
                "test_config": test_config,
                "requirements": requirements,
                "processing_info": {
                    "processing_time": round(processing_time, 2),
                    "timestamp": datetime.now().isoformat(),
                    "status": "completed"
                }
            }
            
            print(f"\n✅ 테스트 설계 완료!")
            print(f"⏱️  처리 시간: {processing_time:.2f}초")
            print(f"📊 총 문제 수: {test_config.get('num_questions', 0)}개")
            print(f"   - 객관식: {test_config.get('num_objective', 0)}개")
            print(f"   - 주관식: {test_config.get('num_subjective', 0)}개")
            
            return result
            
        except Exception as e:
            print(f"❌ 테스트 설계 실패: {e}")
            return {
                "test_summary": "",
                "test_config": {},
                "requirements": {},
                "processing_info": {
                    "processing_time": round(time.time() - start_time, 2),
                    "timestamp": datetime.now().isoformat(),
                    "status": "failed",
                    "error": str(e)
                }
            }
    
    def _analyze_requirements(
        self, 
        keywords: List[str], 
        document_summary: str, 
        document_topics: List[str], 
        user_prompt: str, 
        difficulty: str, 
        test_type: str, 
        time_limit: int
    ) -> Dict[str, Any]:
        """
        사용자 요구사항 분석
        
        Args:
            keywords: 키워드 목록
            document_summary: 문서 요약
            document_topics: 주제 목록
            user_prompt: 사용자 프롬프트
            difficulty: 난이도
            test_type: 테스트 유형
            time_limit: 제한시간
            
        Returns:
            Dict: 분석된 요구사항
        """
        # 요구사항 분석기 사용
        analyzed = self.requirement_analyzer.analyze(user_prompt, keywords, document_summary)
        
        return {
            "user_prompt": user_prompt,
            "keywords": keywords,
            "document_summary": document_summary,
            "document_topics": document_topics,
            "target_difficulty": difficulty,
            "test_type": test_type,
            "time_limit": time_limit,
            "analyzed_requirements": analyzed
        }
    
    def _generate_test_summary(self, requirements: Dict[str, Any]) -> str:
        """
        GPT-4를 사용하여 테스트 요약 생성
        
        Args:
            requirements: 분석된 요구사항
            
        Returns:
            str: 생성된 테스트 요약
        """
        prompt = f"""
다음 정보를 바탕으로 테스트의 목적과 범위를 요약해주세요:

**사용자 요청:**
{requirements['user_prompt']}

**문서 키워드:**
{', '.join(requirements['keywords'])}

**문서 요약:**
{requirements['document_summary']}

**주요 주제:**
{', '.join(requirements['document_topics'])}

**테스트 설정:**
- 난이도: {requirements['target_difficulty']}
- 유형: {requirements['test_type']}
- 제한시간: {requirements['time_limit']}분

다음 형식으로 테스트 요약을 작성해주세요:
1. 테스트 목적
2. 평가 범위
3. 출제 방향
4. 예상 소요시간
"""
        
        try:
            response = openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "당신은 교육 평가 전문가입니다. 주어진 정보를 바탕으로 명확하고 구체적인 테스트 요약을 작성합니다."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"⚠️ 테스트 요약 생성 실패: {e}")
            return f"""테스트 목적: {requirements['user_prompt']}
평가 범위: 제공된 문서 내용
출제 방향: {requirements['target_difficulty']} 난이도
예상 소요시간: {requirements['time_limit']}분"""
    
    def _create_test_config(self, test_summary: str, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """
        테스트 설정 생성
        
        Args:
            test_summary: 생성된 테스트 요약
            requirements: 분석된 요구사항
            
        Returns:
            Dict: 테스트 설정
        """
        # 기본 설정 생성
        base_config = {
            "test_summary": test_summary,
            "difficulty": requirements["target_difficulty"],
            "time_limit": requirements["time_limit"],
            "test_type": requirements["test_type"]
        }
        
        # 문제 수 계산 (사용자 프롬프트 분석)
        user_prompt = requirements["user_prompt"].lower()
        
        # 문제 수 추출 시도
        num_objective = 5  # 기본값
        num_subjective = 3  # 기본값
        
        if "객관식" in user_prompt:
            if "개" in user_prompt:
                try:
                    # "객관식 10개" 같은 패턴 찾기
                    import re
                    matches = re.findall(r'객관식.*?(\d+)', user_prompt)
                    if matches:
                        num_objective = int(matches[0])
                except:
                    pass
        
        if "주관식" in user_prompt:
            if "개" in user_prompt:
                try:
                    import re
                    matches = re.findall(r'주관식.*?(\d+)', user_prompt)
                    if matches:
                        num_subjective = int(matches[0])
                except:
                    pass
        
        # 난이도별 조정
        if requirements["target_difficulty"] == "easy":
            num_objective = max(3, num_objective - 2)
            num_subjective = max(2, num_subjective - 1)
        elif requirements["target_difficulty"] == "hard":
            num_objective = min(10, num_objective + 3)
            num_subjective = min(7, num_subjective + 2)
        
        config = {
            **base_config,
            "num_questions": num_objective + num_subjective,
            "num_objective": num_objective,
            "num_subjective": num_subjective,
            "question_distribution": {
                "objective": num_objective,
                "subjective": num_subjective
            },
            "topics": requirements["document_topics"],
            "keywords": requirements["keywords"],
            "scoring": {
                "objective_points": 2,
                "subjective_points": 5,
                "total_points": (num_objective * 2) + (num_subjective * 5)
            }
        }
        
        return config


# 편의 함수
def design_test_from_analysis(
    keywords: List[str],
    document_summary: str,
    document_topics: List[str],
    user_prompt: str,
    difficulty: str = "medium",
    test_type: str = "mixed",
    time_limit: int = 60
) -> Dict[str, Any]:
    """
    문서 분석 결과로부터 테스트 설계 편의 함수
    
    Args:
        keywords: 문서 키워드
        document_summary: 문서 요약
        document_topics: 주요 주제
        user_prompt: 사용자 요청
        difficulty: 난이도
        test_type: 테스트 유형
        time_limit: 제한시간
        
    Returns:
        테스트 설계 결과
    """
    agent = TestDesignerAgent()
    return agent.design_test(
        keywords, document_summary, document_topics, user_prompt, difficulty, test_type, time_limit
    )


def design_test_from_keywords_file(
    keywords_file_path: str,
    user_prompt: str,
    difficulty: str = "medium",
    test_type: str = "mixed",
    time_limit: int = 60
) -> Dict[str, Any]:
    """
    키워드 파일로부터 테스트 설계 편의 함수
    
    Args:
        keywords_file_path: 키워드/요약 JSON 파일 경로
        user_prompt: 사용자 요청
        difficulty: 난이도
        test_type: 테스트 유형
        time_limit: 제한시간
        
    Returns:
        테스트 설계 결과
    """
    try:
        # 키워드 파일 로드
        with open(keywords_file_path, 'r', encoding='utf-8') as f:
            keywords_data = json.load(f)
        
        content_analysis = keywords_data.get('content_analysis', {})
        
        return design_test_from_analysis(
            keywords=content_analysis.get('keywords', []),
            document_summary=content_analysis.get('summary', ''),
            document_topics=content_analysis.get('main_topics', []),
            user_prompt=user_prompt,
            difficulty=difficulty,
            test_type=test_type,
            time_limit=time_limit
        )
        
    except Exception as e:
        print(f"❌ 키워드 파일 로딩 실패: {e}")
        return {
            "test_summary": "",
            "test_config": {},
            "requirements": {},
            "processing_info": {
                "timestamp": datetime.now().isoformat(),
                "status": "failed",
                "error": f"키워드 파일 로딩 실패: {str(e)}"
            }
        }