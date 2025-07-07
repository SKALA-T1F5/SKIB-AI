"""
테스트 설계 Agent
- 각 문서별 keyword&summary를 input으로 받음
- Gemini 2.5 Pro를 사용하여 전체 테스트 Plan과 문서별 테스트 Plan을 생성
"""

import json
import logging
import os
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langsmith import traceable
from pydantic import BaseModel

from ..base.agent import BaseAgent
from .state import TestDesignerState
from .tools.requirement_analyzer import RequirementAnalyzer
from .tools.test_config_generator import TestConfigGenerator

logger = logging.getLogger(__name__)


class TestGoal(BaseModel):
    test_title: str
    test_summary: str


class TestDesignerAgent(BaseAgent):
    """테스트 설계 전문 Agent"""

    def __init__(self):
        super().__init__(
            name="test_designer",
            state_class=TestDesignerState,
            tools={
                "requirement_analyzer": RequirementAnalyzer(),
                "config_generator": TestConfigGenerator(),
            },
        )
        # Gemini 모니터링 초기화
        self.gemini_monitor = GeminiMonitor()

    async def plan(
        self, input_data: Dict[str, Any], state: TestDesignerState
    ) -> Dict[str, Any]:
        """테스트 설계 계획 수립"""
        return {
            "action": "design_test",
            "steps": [
                "analyze_requirements",
                "generate_test_summary",
                "create_test_config",
                "validate_design",
            ],
            "input_data": input_data,
        }

    async def act(
        self, plan: Dict[str, Any], state: TestDesignerState
    ) -> Dict[str, Any]:
        """
        테스트 설계 실행 - 간소화된 State 업데이트

        최종 목표: { "requirements": requirements, "test_summary": test_summary, "test_config": test_config, "status": "completed" }
        """
        input_data = plan["input_data"]

        # state를 TestDesignerState로 캐스팅
        designer_state = state

        # 1. 요구사항 분석
        self.update_progress(0.2, "요구사항 분석 중...")
        requirements = await self._analyze_requirements(input_data)

        # State 업데이트
        designer_state["test_requirements"] = requirements

        # 2. 테스트 요약 생성
        self.update_progress(0.5, "테스트 요약 생성 중...")
        test_summary = await self._generate_test_summary(requirements, input_data)

        # State 업데이트
        designer_state["test_summary"] = test_summary

        # 3. 테스트 config 생성
        self.update_progress(0.8, "테스트 설정 생성 중...")
        test_config = await self._create_test_config(test_summary, requirements)

        # State 업데이트
        designer_state["test_config"] = test_config

        # 최종 결과 반환 (기존 구조 유지)
        result = {
            "requirements": requirements,
            "test_summary": test_summary,
            "test_config": test_config,
            "status": "completed",
        }

        return result

    async def reflect(
        self, result: Dict[str, Any], state: TestDesignerState
    ) -> tuple[bool, str]:
        """
        결과 검증 - State 정보와 결과의 일관성 확인
        """
        designer_state = state

        # 기존 검증 로직 유지
        required_fields = ["requirements", "test_summary", "test_config"]
        for field in required_fields:
            if field not in result:
                return False, f"필수 필드 '{field}'가 누락되었습니다"

        config = result["test_config"]
        # 다양한 형태의 문제 수 확인
        num_questions = (
            config.get("num_questions", 0)
            or config.get("question_config", {}).get("total_questions", 0)
            or config.get("total_questions", 0)
        )

        if num_questions <= 0:
            return False, "문제 수가 설정되지 않았습니다."

        # State와 결과의 일관성 검증 (간단하게)
        if designer_state.get("test_requirements") != result.get("requirements"):
            return False, "State의 requirements와 결과가 일치하지 않습니다."

        if designer_state.get("test_summary") != result.get("test_summary"):
            return False, "State의 test_summary와 결과가 일치하지 않습니다."

        if designer_state.get("test_config") != result.get("test_config"):
            return False, "State의 test_config와 결과가 일치하지 않습니다."

        return True, "테스트 설계가 성공적으로 완료되었습니다."

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
            "time_limit": input_data.get("time_limit", 60),
        }

    @traceable(
        run_type="chain",
        name="Generate Test Summary",
        metadata={"agent_type": "test_designer"},
    )
    async def _generate_test_summary(
        self, requirements: Dict[str, Any], input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Gemini 2.5 Pro를 사용하여 테스트 계획 생성"""

        # 문서별 정보 정리
        documents_info = []
        if "documents" in input_data:
            for i, doc in enumerate(input_data["documents"]):
                doc_info = f"""
문서 {i+1}: {doc.get('document_name', f'문서_{i+1}')}
- 주요 키워드: {', '.join(doc.get('keywords', [])[:8])}
- 요약: {doc.get('summary', '')[:200]}...
- 주요 주제: {', '.join(doc.get('main_topics', [])[:5])}
"""
                documents_info.append(doc_info)

        user_prompt = f"""
당신은 교육 평가 전문가입니다. 제공된 여러 문서의 내용을 분석하여 종합적인 테스트 계획을 수립해주세요.

## 분석 대상 문서들:
{chr(10).join(documents_info)}

## 사용자 요구사항 (문제 수, 난이도 등 모든 요구사항을 반영해주세요):
{requirements.get('user_prompt', '표준 테스트 계획을 수립해주세요')}

다음 JSON 형식으로 응답해주세요:

```json
{{
    "name": "전체 테스트의 적절한 이름", 
    "test_summary": "이 테스트의 목적과 평가 범위를 설명하는 요약 (200자 이내)",
    "difficulty_level": "NORMAL",
    "limited_time": 90,
    "pass_score": 70,
    "retake": true,
    "document_configs": [
        {{
            "document_id": 1,
            "keywords": ["문서1의 핵심 키워드 5-8개"],
            "recommended_objective": 5,
            "recommended_subjective": 3
        }},
        {{
            "document_id": 2,
            "keywords": ["문서2의 핵심 키워드 5-8개"],
            "recommended_objective": 4,
            "recommended_subjective": 2
        }}
    ]
}}
```

## 지침:
1. **사용자 요구사항 최우선**: 위의 사용자 요구사항에 명시된 문제 수, 난이도, 기타 조건을 정확히 반영하세요
2. **전체 테스트명**: 모든 문서의 주제를 아우르는 포괄적인 이름
3. **테스트 요약**: 전체 테스트의 목적과 평가 범위를 명확히 설명
4. **제한시간**: 문서 수와 문제 수를 고려하여 적절히 설정 (60-120분)
5. **통과점수**: 난이도에 따라 조정 (EASY: 60%, NORMAL: 70%, HARD: 80%)
6. **문서별 키워드**: 각 문서에서 가장 중요한 키워드 5-8개 선별
7. **문제 수 추천**: 사용자가 요청한 문제 수가 있다면 그대로 반영하고, 없다면 문서의 복잡도와 중요도에 따라 조정
   - 객관식: 2-10개 (기본 개념 확인)
   - 주관식: 1-8개 (심화 이해 평가)
8. **객관식/주관식 문제 수 조정**: 객관식/주관식 문제 수를 적절히 배분.

반드시 유효한 JSON 형식으로만 응답하세요.
"""

        try:
            model_name = "gemini-2.5-flash"
            logger.info(f"🤖 {model_name}로 테스트 계획 생성 중...")

            # LangChain 기반 Gemini 호출 (실제 실행)
            llm = ChatGoogleGenerativeAI(
                model=model_name,
                temperature=0.3,
                max_tokens=3000,
                max_retries=2,
                timeout=60,
                api_key=os.environ.get("GOOGLE_API_KEY"),
            )

            # 메시지 생성
            messages = [HumanMessage(content=user_prompt)]

            # ChatPromptTemplate 사용
            prompt_template = ChatPromptTemplate.from_messages([("human", "{content}")])

            # 체인 생성 및 실행
            chain = prompt_template | llm
            response = chain.invoke({"content": user_prompt})

            # 응답 처리
            if response and response.content:
                # 사용량 및 비용 모니터링 (LangChain 응답 메타데이터 활용)
                if hasattr(response, "usage_metadata") and response.usage_metadata:
                    self.gemini_monitor.print_usage_summary(
                        model_name, response.usage_metadata
                    )
                    self.gemini_monitor.log_usage(
                        model_name,
                        response.usage_metadata,
                        function_name="test_designer_generate_test_summary_langchain",
                        additional_metadata={
                            "agent_type": "test_designer",
                            "document_count": len(input_data.get("documents", [])),
                            "user_prompt_length": len(
                                requirements.get("user_prompt", "")
                            ),
                        },
                    )

                raw_content = response.content.strip()
                logger.debug(f"📄 응답 내용 미리보기: {raw_content[:200]}...")

                # JSON 파싱
                if "```json" in raw_content:
                    raw_content = (
                        raw_content.split("```json")[1].split("```")[0].strip()
                    )
                elif "```" in raw_content:
                    raw_content = raw_content.split("```")[1].split("```")[0].strip()

                test_plan_data = json.loads(raw_content)
                logger.info(f"✅ {model_name} 테스트 계획 생성 완료")
                return test_plan_data
            else:
                logger.warning(f"⚠️ Gemini 응답이 차단됨")
                raise Exception("Gemini 응답이 차단되었습니다")

        except Exception as e:
            self.logger.error(f"테스트 계획 생성 실패: {e}")
            # 기본 계획 반환
            return {
                "name": "종합 평가 테스트",
                "test_summary": "제공된 문서들의 핵심 내용을 종합적으로 평가하는 테스트입니다.",
                "difficulty_level": requirements.get("target_difficulty", "NORMAL"),
                "limited_time": 90,
                "pass_score": 70,
                "retake": True,
                "document_configs": [
                    {
                        "document_id": i + 1,
                        "keywords": doc.get("keywords", [])[:6],
                        "recommended_objective": 4,
                        "recommended_subjective": 2,
                    }
                    for i, doc in enumerate(input_data.get("documents", []))
                ],
            }

    async def _create_test_config(
        self, test_summary: str, requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """테스트 설정 생성"""
        # config_generator = self.config_generator  # 원래 구조 유지

        # 기본 설정 생성
        base_config = {
            "test_summary": test_summary,
            "difficulty": requirements["target_difficulty"],
            "time_limit": requirements["time_limit"],
            "test_type": requirements["test_type"],
        }

        # 문제 수 계산 (사용자 프롬프트 분석) - 주석처리: Gemini가 직접 판단하도록 변경
        # user_prompt = requirements["user_prompt"].lower()

        # # 문제 수 추출 시도
        # num_objective = 5  # 기본값
        # num_subjective = 3  # 기본값

        # if "객관식" in user_prompt:
        #     if any(word in user_prompt for word in ["개", "문제"]):
        #         try:
        #             # "객관식 10개" 또는 "객관식 10문제" 같은 패턴 찾기
        #             import re

        #             matches = re.findall(r"객관식.*?(\d+)", user_prompt)
        #             if matches:
        #                 num_objective = int(matches[0])
        #             # TODO : 예외 처리 개선
        #         except:  # noqa: E722
        #             pass

        # if "주관식" in user_prompt:
        #     if any(word in user_prompt for word in ["개", "문제"]):
        #         try:
        #             import re

        #             matches = re.findall(r"주관식.*?(\d+)", user_prompt)
        #             if matches:
        #                 num_subjective = int(matches[0])
        #             # TODO : 예외 처리 개선
        #         except:  # noqa: E722
        #             pass

        # 기본값 설정 (Gemini가 사용자 프롬프트를 보고 조정할 것)
        num_objective = 5  # 기본값
        num_subjective = 3  # 기본값

        # 난이도별 조정 (주석처리)
        # if requirements["target_difficulty"] == "easy":
        #     num_objective = max(3, num_objective - 2)
        #     num_subjective = max(2, num_subjective - 1)
        # elif requirements["target_difficulty"] == "hard":
        #     num_objective = min(10, num_objective + 3)
        #     num_subjective = min(7, num_subjective + 2)

        config = {
            **base_config,
            "num_questions": num_objective + num_subjective,
            "num_objective": num_objective,
            "num_subjective": num_subjective,
            "question_distribution": {
                "objective": num_objective,
                "subjective": num_subjective,
            },
            "topics": requirements["document_topics"],
            "keywords": requirements["keywords"],
            "scoring": {
                "objective_points": 2,
                "subjective_points": 5,
                "total_points": (num_objective * 2) + (num_subjective * 5),
            },
        }

        return config


def _convert_document_name_to_collection(document_name: str) -> str:
    """문서명을 VectorDB collection명으로 변환"""
    try:
        from utils.naming import filename_to_collection

        # 문서명에서 .pdf 제거 후 collection명으로 변환
        clean_name = document_name.replace(".pdf", "").replace(".PDF", "")
        collection_name = filename_to_collection(clean_name)

        # 특정 패턴 보정 (실제 VectorDB collection명과 일치하도록)
        if collection_name.startswith("c_2_ags"):
            collection_name = collection_name.replace("c_2_ags", "doc_2_ags")
        elif collection_name.startswith("2_ags"):
            collection_name = "doc_" + collection_name

        return collection_name
    except ImportError:
        # utils.naming이 없으면 기본 변환 로직 사용
        clean_name = document_name.replace(".pdf", "").replace(".PDF", "")
        # 간단한 변환: 공백을 언더스코어로, 특수문자 제거
        collection_name = clean_name.replace(" ", "_").replace("-", "_")
        collection_name = "".join(
            c.lower() if c.isalnum() or c == "_" else "_" for c in collection_name
        )
        # 연속된 언더스코어 제거
        while "__" in collection_name:
            collection_name = collection_name.replace("__", "_")

        # 특정 패턴 보정
        if collection_name.startswith("2_ags"):
            collection_name = "doc_" + collection_name

        return collection_name.strip("_")


def design_test_from_documents(
    documents: List[Dict[str, Any]],
    user_prompt: str = "표준 테스트 계획을 수립해주세요",
    difficulty: str = "NORMAL",
    test_type: str = "mixed",
    time_limit: int = 90,
    save_files: bool = True,
) -> Dict[str, Any]:
    """
    여러 문서의 키워드/요약으로부터 테스트 계획 설계

    Args:
        documents: 문서 정보 리스트
            [{"document_id": 1, "document_name": "문서명", "keywords": [...], "summary": "...", "main_topics": [...]}]
        user_prompt: 사용자 요청
        difficulty: 난이도 (EASY, NORMAL, HARD)
        test_type: 테스트 유형
        time_limit: 제한시간
        save_files: 파일로 저장할지 여부

    Returns:
        테스트 계획 결과 (전체 테스트 Plan + 문서별 테스트 Plan)
    """
    import asyncio

    agent = TestDesignerAgent()

    input_data = {
        "documents": documents,
        "user_prompt": user_prompt,
        "difficulty": difficulty,
        "test_type": test_type,
        "time_limit": time_limit,
    }

    # 비동기 실행
    async def run():
        await agent.initialize()
        result = await agent.execute(input_data)

        if save_files and result.get("output", {}).get("status") == "completed":
            _save_test_plans(result.get("output", {}), documents)

        return result

    return asyncio.run(run())


def _save_test_plans(result: Dict[str, Any], documents: List[Dict[str, Any]]):
    """테스트 계획을 분리하여 저장"""
    import os
    from datetime import datetime

    # 타임스탬프 생성
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 디렉토리 생성
    total_dir = "data/outputs/total_test_plan"
    document_dir = "data/outputs/document_test_plan"
    os.makedirs(total_dir, exist_ok=True)
    os.makedirs(document_dir, exist_ok=True)

    # 1. 전체 테스트 plan 저장 (여러 문서들의 keyword&summary 활용한 통합 계획)
    if "test_summary" in result:
        test_summary = result["test_summary"]

        # 전체 테스트 계획 파일
        total_test_plan = {
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "total_documents": len(documents),
                "document_names": [
                    doc.get("document_name", f"문서_{doc.get('document_id', i+1)}")
                    for i, doc in enumerate(documents)
                ],
            },
            "test_plan": {
                "name": test_summary.get("name", "종합 테스트"),
                "test_summary": test_summary.get("test_summary", ""),
                "difficulty_level": test_summary.get("difficulty_level", "NORMAL"),
                "limited_time": test_summary.get("limited_time", 90),
                "pass_score": test_summary.get("pass_score", 70),
                "retake": test_summary.get("retake", True),
            },
            "aggregated_info": {
                "all_keywords": list(
                    set([kw for doc in documents for kw in doc.get("keywords", [])])
                ),
                "all_summaries": [doc.get("summary", "") for doc in documents],
                "all_topics": list(
                    set(
                        [
                            topic
                            for doc in documents
                            for topic in doc.get("main_topics", [])
                        ]
                    )
                ),
            },
        }

        total_filename = f"total_test_plan_{timestamp}.json"
        total_path = os.path.join(total_dir, total_filename)

        with open(total_path, "w", encoding="utf-8") as f:
            json.dump(total_test_plan, f, ensure_ascii=False, indent=2)

        logger.info(f"✅ 전체 테스트 계획 저장: {total_path}")

    # 2. 문서별 테스트 plan 저장 (document_id, keywords, 추천 문제수)
    if "test_summary" in result and "document_configs" in result["test_summary"]:
        document_configs = result["test_summary"]["document_configs"]

        # 문서별 테스트 계획 파일
        document_test_plan = {
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "total_documents": len(document_configs),
            },
            "document_plans": [],
        }

        for i, config in enumerate(document_configs):
            # 원본 문서 정보 찾기 (인덱스 기반)
            if i < len(documents):
                original_doc = documents[i]
            else:
                original_doc = {}

            # 원본 문서명을 collection명으로 변환
            original_document_name = original_doc.get(
                "document_name", f"문서_{config.get('document_id', i+1)}"
            )
            collection_name = _convert_document_name_to_collection(
                original_document_name
            )

            doc_plan = {
                "document_id": config.get("document_id"),
                "document_name": collection_name,  # collection명으로 저장
                "original_document_name": original_document_name,  # 원본 문서명도 보존
                "keywords": config.get("keywords", []),
                "summary": original_doc.get("summary", ""),
                "main_topics": original_doc.get("main_topics", []),
                "recommended_questions": {
                    "objective": config.get("recommended_objective", 5),
                    "subjective": config.get("recommended_subjective", 3),
                    "total": config.get("recommended_objective", 5)
                    + config.get("recommended_subjective", 3),
                },
            }
            document_test_plan["document_plans"].append(doc_plan)

        document_filename = f"document_test_plan_{timestamp}.json"
        document_path = os.path.join(document_dir, document_filename)

        with open(document_path, "w", encoding="utf-8") as f:
            json.dump(document_test_plan, f, ensure_ascii=False, indent=2)

        logger.info(f"✅ 문서별 테스트 계획 저장: {document_path}")


# 기존 함수 호환성 유지
def design_test_from_analysis(
    keywords: List[str],
    document_summary: str,
    document_topics: List[str],
    user_prompt: str,
    difficulty: str = "NORMAL",
    test_type: str = "mixed",
    time_limit: int = 60,
) -> Dict[str, Any]:
    """기존 함수 호환성 유지 (단일 문서용)"""
    documents = [
        {
            "document_id": 1,
            "document_name": "단일 문서",
            "keywords": keywords,
            "summary": document_summary,
            "main_topics": document_topics,
        }
    ]

    return design_test_from_documents(
        documents=documents,
        user_prompt=user_prompt,
        difficulty=difficulty,
        test_type=test_type,
        time_limit=time_limit,
    )
