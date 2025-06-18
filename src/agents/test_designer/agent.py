"""
테스트 설계 Agent
- 키워드와 문서 요약을 분석
- 사용자 프롬프트를 GPT-4에 전달
- 테스트 요약 및 config 생성
"""

from typing import Dict, Any, List
from ..base.agent import BaseAgent
from ..base.state import BaseState, TestDesignerState, update_state_progress
from .tools.requirement_analyzer import RequirementAnalyzer
from .tools.test_config_generator import TestConfigGenerator
import openai
import json


class TestDesignerAgent(BaseAgent):
    """테스트 설계 전문 Agent"""
    
    def __init__(self):
        super().__init__(
            name="test_designer",
            state_class=TestDesignerState,
            tools={
                "requirement_analyzer": RequirementAnalyzer(),
                "config_generator": TestConfigGenerator()
            }
        )
    
    async def plan(self, input_data: Dict[str, Any], state: BaseState) -> Dict[str, Any]:
        """테스트 설계 계획 수립"""
        return {
            "action": "design_test",
            "steps": [
                "analyze_requirements",
                "generate_test_summary", 
                "create_test_config",
                "validate_design"
            ],
            "input_data": input_data
        }
    
    async def act(self, plan: Dict[str, Any], state: BaseState) -> Dict[str, Any]:
        """테스트 설계 실행"""
        input_data = plan["input_data"]
        
        # 1. 요구사항 분석
        self.update_progress(0.2, "요구사항 분석 중...")
        requirements = await self._analyze_requirements(input_data)
        
        # 2. 테스트 요약 생성
        self.update_progress(0.5, "테스트 요약 생성 중...")
        test_summary = await self._generate_test_summary(requirements, input_data)
        
        # 3. 테스트 config 생성
        self.update_progress(0.8, "테스트 설정 생성 중...")
        test_config = await self._create_test_config(test_summary, requirements)
        
        return {
            "requirements": requirements,
            "test_summary": test_summary,
            "test_config": test_config,
            "status": "completed"
        }
    
    async def reflect(self, result: Dict[str, Any], state: BaseState) -> tuple[bool, str]:
        """결과 검증"""
        required_fields = ["requirements", "test_summary", "test_config"]
        
        for field in required_fields:
            if field not in result:
                return False, f"필수 필드 '{field}'가 누락되었습니다"
        
        # 테스트 config 검증
        config = result["test_config"]
        if not config.get("num_questions") or config["num_questions"] <= 0:
            return False, "유효하지 않은 문제 수입니다"
        
        return True, "테스트 설계가 성공적으로 완료되었습니다"
    
    async def _analyze_requirements(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """요구사항 분석"""
        # analyzer = self.requirement_analyzer  # 원래 구조 유지
        
        return {
            "user_prompt": input_data.get("user_prompt", ""),
            "keywords": input_data.get("keywords", []),
            "document_summary": input_data.get("document_summary", ""),
            "document_topics": input_data.get("document_topics", []),
            "target_difficulty": input_data.get("difficulty", "medium"),
            "test_type": input_data.get("test_type", "mixed"),
            "time_limit": input_data.get("time_limit", 60)
        }
    
    async def _generate_test_summary(self, requirements: Dict[str, Any], input_data: Dict[str, Any]) -> str:
        """GPT-4를 사용하여 테스트 요약 생성"""
        
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
            from openai import AsyncOpenAI
            client = AsyncOpenAI()
            
            response = await client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "당신은 교육 평가 전문가입니다. 주어진 정보를 바탕으로 명확하고 구체적인 테스트 요약을 작성합니다."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            self.logger.error(f"테스트 요약 생성 실패: {e}")
            return f"테스트 목적: {requirements['user_prompt']}\n평가 범위: 제공된 문서 내용\n출제 방향: {requirements['target_difficulty']} 난이도"
    
    async def _create_test_config(self, test_summary: str, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """테스트 설정 생성"""
        # config_generator = self.config_generator  # 원래 구조 유지
        
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
    
    # BaseAgent abstract methods 구현
    async def plan(self, input_data: Dict[str, Any], state: BaseState) -> Dict[str, Any]:
        """작업 계획 수립"""
        return {"action": "analyze_and_design", "input": input_data}
    
    async def act(self, plan: Dict[str, Any], state: BaseState) -> Dict[str, Any]:
        """실제 작업 수행"""
        input_data = plan["input"]
        
        # 요구사항 분석
        requirements = await self._analyze_requirements(input_data)
        
        # 테스트 요약 생성
        test_summary = await self._generate_test_summary(requirements, input_data)
        
        # 테스트 설정 생성
        test_config = await self._create_test_config(test_summary, requirements)
        
        return {
            "test_summary": test_summary,
            "test_config": test_config,
            "requirements": requirements
        }
    
    async def reflect(self, result: Dict[str, Any], state: BaseState) -> tuple[bool, str]:
        """결과 검증"""
        if "test_summary" in result and "test_config" in result:
            config = result["test_config"]
            # 다양한 형태의 문제 수 확인
            num_questions = (
                config.get("num_questions", 0) or 
                config.get("question_config", {}).get("total_questions", 0) or
                config.get("total_questions", 0)
            )
            if num_questions > 0:
                return True, "테스트 설계가 성공적으로 완료되었습니다."
            else:
                return False, "문제 수가 설정되지 않았습니다."
        return False, "테스트 요약이나 설정이 생성되지 않았습니다."


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
    문서 분석 결과로부터 테스트 설계
    
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
    import asyncio
    
    agent = TestDesignerAgent()
    
    input_data = {
        "keywords": keywords,
        "document_summary": document_summary,
        "document_topics": document_topics,
        "user_prompt": user_prompt,
        "difficulty": difficulty,
        "test_type": test_type,
        "time_limit": time_limit
    }
    
    # 비동기 실행
    async def run():
        await agent.initialize()
        result = await agent.execute(input_data)
        return result
    
    return asyncio.run(run())