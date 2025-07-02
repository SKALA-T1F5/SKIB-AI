"""
Test Generation Pipeline - LangGraph 기반 테스트 생성 파이프라인
- BasePipeline 상속
- Celery Task 기반 분산 처리
- Document SubGraph를 통한 배치별 문제 생성
- 품질 기반 조건부 분기
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from langgraph.graph import END, StateGraph
from langsmith import traceable

from src.pipelines.base.pipeline import BasePipeline
from src.pipelines.test_generation.state import TestGenerationState

logger = logging.getLogger(__name__)


class TestGenerationPipeline(BasePipeline[TestGenerationState]):
    """테스트 생성 전용 LangGraph Pipeline"""

    def _get_state_schema(self) -> type:
        """State 스키마 반환"""
        return TestGenerationState

    def _get_node_list(self) -> List[str]:
        """메인 파이프라인 노드 목록"""
        return ["load_test_plans", "create_smart_batches", "process_document_batches", "collect_results"]

    def _get_default_state(self) -> Dict[str, Any]:
        """기본 State 설정"""
        return {
            "pipeline_id": str(uuid.uuid4()),
            "session_id": str(uuid.uuid4()),
            "current_step": "load_test_plans",
            "processing_status": "pending",
            "progress_percentage": 0.0,
            "started_at": datetime.now().isoformat(),
            "retry_count": 0,
            "total_batches": 0,
            "completed_batches": 0,
            "batch_quality_scores": {},
            "regeneration_attempts": {},
            "current_batch_processing": [],
            "batch_processing_strategy": "parallel",
        }

    def _build_workflow(self) -> StateGraph:
        """메인 파이프라인 워크플로우 구성"""
        workflow = StateGraph(TestGenerationState)

        # 메인 노드들 추가
        workflow.add_node("load_test_plans", self._load_test_plans_node)
        workflow.add_node("create_smart_batches", self._create_smart_batches_node)
        workflow.add_node(
            "process_document_batches", self._process_document_batches_node
        )
        workflow.add_node("collect_results", self._collect_results_node)
        workflow.add_node("error_handler", self._error_handler_node)

        # Document SubGraph 추가
        document_subgraph = self._build_document_subgraph()
        workflow.add_node("document_subgraph", document_subgraph)

        # 워크플로우 연결
        workflow.set_entry_point("load_test_plans")

        workflow.add_edge("load_test_plans", "create_smart_batches")
        workflow.add_edge("create_smart_batches", "process_document_batches")
        workflow.add_edge("process_document_batches", "collect_results")
        workflow.add_edge("collect_results", END)

        # 에러 처리
        workflow.add_edge("error_handler", END)

        return workflow

    def _build_document_subgraph(self) -> StateGraph:
        """Document 처리 SubGraph 구성"""
        subgraph = StateGraph(TestGenerationState)

        # SubGraph 노드들
        subgraph.add_node("vector_search", self._vector_search_node)
        subgraph.add_node("generate_questions", self._generate_questions_node)
        subgraph.add_node("review_questions", self._review_questions_node)
        subgraph.add_node("regenerate_questions", self._regenerate_questions_node)
        subgraph.add_node("approve_batch", self._approve_batch_node)
        subgraph.add_node("retry_strategy", self._retry_strategy_node)

        # SubGraph 워크플로우
        subgraph.set_entry_point("vector_search")

        subgraph.add_edge("vector_search", "generate_questions")
        subgraph.add_edge("generate_questions", "review_questions")

        # 조건부 분기 - 품질 기반
        subgraph.add_conditional_edges(
            "review_questions",
            self._route_after_review,
            {
                "approve": "approve_batch",
                "regenerate": "regenerate_questions",
                "retry_strategy": "retry_strategy",
            },
        )

        subgraph.add_edge("regenerate_questions", "review_questions")
        subgraph.add_edge("retry_strategy", "vector_search")
        subgraph.add_edge("approve_batch", END)

        return subgraph.compile()

    # ============ 메인 파이프라인 노드들 ============

    @traceable(name="load_test_plans")
    async def _load_test_plans_node(
        self, state: TestGenerationState
    ) -> TestGenerationState:
        """Test Plan 로드 및 Redis 저장"""
        self.logger.info("📋 Test Plan 로드 시작")

        try:
            # 기존 TestPlanHandler 활용
            from src.agents.question_generator.tools.test_plan_handler import (
                TestPlanHandler,
            )

            handler = TestPlanHandler()

            # State에서 test_config 확인
            test_config = state.get("test_config", {})

            if (
                "total_test_plan_data" in test_config
                and "document_test_plan_data" in test_config
            ):
                # 직접 전달된 데이터 사용
                total_plan = test_config["total_test_plan_data"]
                document_plan = test_config["document_test_plan_data"]
                self.logger.info("📋 직접 전달된 Test Plan 데이터 사용")
            else:
                # 자동으로 최신 파일 로드
                total_plan, document_plan = handler.load_latest_test_plans()
                if not total_plan or not document_plan:
                    raise Exception("Test plan 파일을 찾을 수 없습니다")
                self.logger.info("📋 파일에서 Test Plan 로드 완료")

            return {
                **state,
                "total_test_plan": total_plan,
                "document_test_plan": document_plan,
                "current_step": "create_smart_batches",
                "progress_percentage": 20.0,
            }

        except Exception as e:
            self.logger.error(f"❌ Test Plan 로드 실패: {e}")
            return {
                **state,
                "processing_status": "failed",
                "error_message": str(e),
                "current_step": "error_handler",
            }

    @traceable(name="create_smart_batches")
    async def _create_smart_batches_node(
        self, state: TestGenerationState
    ) -> TestGenerationState:
        """문서별 배치 생성 및 처리 전략 결정"""
        self.logger.info("🎯 스마트 배치 생성 시작")

        try:
            document_plan = state["document_test_plan"]
            document_plans = document_plan.get("document_plans", [])

            processing_batches = []

            for i, doc_plan in enumerate(document_plans):
                batch = {
                    "batch_id": i + 1,
                    "document_id": doc_plan.get("document_id"),
                    "document_name": doc_plan.get("document_name", f"document_{i+1}"),
                    "keywords": doc_plan.get("keywords", []),
                    "target_questions": {
                        "objective": doc_plan.get("recommended_questions", {}).get(
                            "objective", 3
                        ),
                        "subjective": doc_plan.get("recommended_questions", {}).get(
                            "subjective", 2
                        ),
                    },
                    "difficulty": doc_plan.get("difficulty_level", "medium"),
                    "priority": doc_plan.get("priority", "medium"),
                }
                processing_batches.append(batch)

            # 처리 전략 결정 (배치 수에 따라)
            if len(processing_batches) <= 2:
                strategy = "parallel"
            elif len(processing_batches) <= 5:
                strategy = "parallel"  # 우선 병렬로 시도
            else:
                strategy = "hybrid"  # 큰 배치는 혼합 전략

            self.logger.info(
                f"✅ {len(processing_batches)}개 배치 생성, 전략: {strategy}"
            )

            return {
                **state,
                "processing_batches": processing_batches,
                "total_batches": len(processing_batches),
                "batch_processing_strategy": strategy,
                "current_step": "process_document_batches",
                "progress_percentage": 40.0,
            }

        except Exception as e:
            self.logger.error(f"❌ 배치 생성 실패: {e}")
            return {
                **state,
                "processing_status": "failed",
                "error_message": str(e),
                "current_step": "error_handler",
            }

    @traceable(name="process_document_batches")
    async def _process_document_batches_node(
        self, state: TestGenerationState
    ) -> TestGenerationState:
        """Document SubGraph를 통한 배치 처리 관리"""
        self.logger.info("🔄 Document 배치 처리 시작")

        try:
            processing_batches = state["processing_batches"]
            strategy = state["batch_processing_strategy"]

            if strategy == "parallel":
                # 모든 배치를 병렬로 처리
                current_processing = [batch["batch_id"] for batch in processing_batches]
            else:
                # 순차 또는 제한된 병렬 처리
                current_processing = (
                    [processing_batches[0]["batch_id"]] if processing_batches else []
                )

            return {
                **state,
                "current_batch_processing": current_processing,
                "current_step": "document_subgraph",
                "progress_percentage": 60.0,
            }

        except Exception as e:
            self.logger.error(f"❌ 배치 처리 관리 실패: {e}")
            return {
                **state,
                "processing_status": "failed",
                "error_message": str(e),
                "current_step": "error_handler",
            }

    @traceable(name="collect_results")
    async def _collect_results_node(
        self, state: TestGenerationState
    ) -> TestGenerationState:
        """모든 배치 결과 수집 및 최종 테스트 생성"""
        self.logger.info("📊 결과 수집 시작")

        try:
            pipeline_id = state["pipeline_id"]
            total_batches = state["total_batches"]

            # Redis에서 모든 배치 결과 수집
            from db.redisDB.testgen_session_manager import (
                load_batch_questions,
                save_final_test,
            )

            all_questions = []
            successful_batches = 0
            total_quality_scores = []

            for batch_id in range(1, total_batches + 1):
                questions = await load_batch_questions(pipeline_id, batch_id)
                if questions:
                    all_questions.extend(questions)
                    successful_batches += 1

                    # 품질 점수 수집
                    batch_quality = state.get("batch_quality_scores", {}).get(
                        batch_id, 0.0
                    )
                    if batch_quality > 0:
                        total_quality_scores.append(batch_quality)

            # 최종 테스트 데이터 구성
            final_test_data = {
                "total_questions": len(all_questions),
                "questions": all_questions,
                "metadata": {
                    "pipeline_id": pipeline_id,
                    "successful_batches": successful_batches,
                    "total_batches": total_batches,
                    "average_quality_score": (
                        sum(total_quality_scores) / len(total_quality_scores)
                        if total_quality_scores
                        else 0.0
                    ),
                    "questions_by_type": {
                        "objective": len(
                            [q for q in all_questions if q.get("type") == "OBJECTIVE"]
                        ),
                        "subjective": len(
                            [q for q in all_questions if q.get("type") == "SUBJECTIVE"]
                        ),
                    },
                    "completed_at": datetime.now().isoformat(),
                },
            }

            # Redis에 최종 결과 저장
            await save_final_test(pipeline_id, final_test_data)

            self.logger.info(f"✅ 결과 수집 완료: {len(all_questions)}개 문제")

            return {
                **state,
                "processing_status": "completed",
                "completed_batches": successful_batches,
                "current_step": "completed",
                "progress_percentage": 100.0,
                "completed_at": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"❌ 결과 수집 실패: {e}")
            return {
                **state,
                "processing_status": "failed",
                "error_message": str(e),
                "current_step": "error_handler",
            }

    # ============ Document SubGraph 노드들 ============

    @traceable(name="vector_search_subgraph")
    async def _vector_search_node(
        self, state: TestGenerationState
    ) -> TestGenerationState:
        """VectorDB 검색 (Celery Task 호출)"""
        self.logger.info("🔍 Vector Search 노드 시작")

        try:
            from src.pipelines.test_generation.celery_tasks import vector_search_task

            current_batch_id = state["current_batch_processing"][0]  # 첫 번째 배치 처리
            batch_info = None

            for batch in state["processing_batches"]:
                if batch["batch_id"] == current_batch_id:
                    batch_info = batch
                    break

            if not batch_info:
                raise Exception(f"배치 {current_batch_id} 정보를 찾을 수 없습니다")

            # Celery Task 실행
            task = vector_search_task.delay(
                pipeline_id=state["pipeline_id"],
                batch_id=current_batch_id,
                keywords=batch_info["keywords"],
                document_name=batch_info["document_name"],
            )

            # 결과 대기 (비동기 처리를 위해 짧은 대기)
            result = task.get(timeout=300)  # 5분 대기

            if result["status"] != "success":
                raise Exception(f"Vector search 실패: {result.get('error')}")

            self.logger.info(
                f"✅ Vector Search 완료: {result['contexts_count']}개 컨텍스트"
            )

            return {**state, "current_step": "generate_questions"}

        except Exception as e:
            self.logger.error(f"❌ Vector Search 실패: {e}")
            return {
                **state,
                "processing_status": "failed",
                "error_message": str(e),
                "current_step": "error_handler",
            }

    @traceable(name="generate_questions_subgraph")
    async def _generate_questions_node(
        self, state: TestGenerationState
    ) -> TestGenerationState:
        """문제 생성 (Celery Task 호출)"""
        self.logger.info("🤖 Question Generation 노드 시작")

        try:
            from src.pipelines.test_generation.celery_tasks import (
                question_generation_task,
            )

            current_batch_id = state["current_batch_processing"][0]
            batch_info = None

            for batch in state["processing_batches"]:
                if batch["batch_id"] == current_batch_id:
                    batch_info = batch
                    break

            # Celery Task 실행
            task = question_generation_task.delay(
                pipeline_id=state["pipeline_id"],
                batch_id=current_batch_id,
                target_questions=batch_info["target_questions"],
                document_metadata={
                    "document_name": batch_info["document_name"],
                    "document_id": batch_info["document_id"],
                    "keywords": batch_info["keywords"],
                    "difficulty": batch_info["difficulty"],
                },
            )

            result = task.get(timeout=600)  # 10분 대기

            if result["status"] != "success":
                raise Exception(f"Question generation 실패: {result.get('error')}")

            # 품질 점수 업데이트
            batch_quality_scores = state.get("batch_quality_scores", {})
            batch_quality_scores[current_batch_id] = result["quality_score"]

            self.logger.info(
                f"✅ Question Generation 완료: {result['questions_generated']}개 문제"
            )

            return {
                **state,
                "batch_quality_scores": batch_quality_scores,
                "current_step": "review_questions",
            }

        except Exception as e:
            self.logger.error(f"❌ Question Generation 실패: {e}")
            return {
                **state,
                "processing_status": "failed",
                "error_message": str(e),
                "current_step": "error_handler",
            }

    async def _review_questions_node(
        self, state: TestGenerationState
    ) -> TestGenerationState:
        """문제 품질 검토"""
        current_batch_id = state["current_batch_processing"][0]
        quality_score = state.get("batch_quality_scores", {}).get(current_batch_id, 0.0)

        self.logger.info(
            f"📊 품질 검토: 배치 {current_batch_id}, 점수 {quality_score:.3f}"
        )

        return {**state, "current_step": "route_decision"}

    async def _regenerate_questions_node(
        self, state: TestGenerationState
    ) -> TestGenerationState:
        """문제 재생성"""
        self.logger.info("🔄 문제 재생성 시작")

        current_batch_id = state["current_batch_processing"][0]
        regeneration_attempts = state.get("regeneration_attempts", {})
        regeneration_attempts[current_batch_id] = (
            regeneration_attempts.get(current_batch_id, 0) + 1
        )

        return {
            **state,
            "regeneration_attempts": regeneration_attempts,
            "current_step": "generate_questions",  # 문제 생성으로 다시 이동
        }

    async def _approve_batch_node(
        self, state: TestGenerationState
    ) -> TestGenerationState:
        """배치 승인 및 완료"""
        current_batch_id = state["current_batch_processing"][0]
        completed_batches = state.get("completed_batches", 0) + 1

        self.logger.info(f"✅ 배치 {current_batch_id} 승인 완료")

        return {
            **state,
            "completed_batches": completed_batches,
            "current_step": "completed",
        }

    async def _retry_strategy_node(
        self, state: TestGenerationState
    ) -> TestGenerationState:
        """재시도 전략 적용"""
        self.logger.info("🔄 재시도 전략 적용")

        return {**state, "current_step": "vector_search"}  # Vector search부터 다시 시작

    async def _error_handler_node(
        self, state: TestGenerationState
    ) -> TestGenerationState:
        """에러 처리"""
        error_message = state.get("error_message", "Unknown error")
        self.logger.error(f"❌ Pipeline 에러: {error_message}")

        return {
            **state,
            "processing_status": "failed",
            "completed_at": datetime.now().isoformat(),
        }

    # ============ 조건부 분기 라우터들 ============

    def _route_after_review(self, state: TestGenerationState) -> str:
        """품질 검토 후 분기 결정"""
        current_batch_id = state["current_batch_processing"][0]
        quality_score = state.get("batch_quality_scores", {}).get(current_batch_id, 0.0)
        regeneration_attempts = state.get("regeneration_attempts", {}).get(
            current_batch_id, 0
        )

        # 분기 로직
        if quality_score >= 0.7:
            return "approve"
        elif regeneration_attempts >= 2:
            return "retry_strategy"  # 최대 재생성 시도 초과시 다른 전략
        else:
            return "regenerate"

    # ============ BasePipeline 필수 메서드들 ============

    async def run(
        self, input_data: Dict[str, Any], session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Pipeline 실행"""
        try:
            # 초기 상태 설정
            initial_state = {**self._get_default_state(), **input_data}

            if session_id:
                initial_state["session_id"] = session_id

            self.logger.info(
                f"🚀 Test Generation Pipeline 시작: {initial_state['pipeline_id']}"
            )

            # LangGraph 실행
            final_state = await self.compiled_graph.ainvoke(
                initial_state, config={"recursion_limit": 50}
            )

            # 결과 반환
            return {
                "status": final_state.get("processing_status", "completed"),
                "pipeline_id": final_state["pipeline_id"],
                "total_questions": final_state.get("total_questions", 0),  # 정확한 값
                "processing_time": self._calculate_processing_time(final_state),
                "batch_results": final_state.get("batch_quality_scores", {}),
                "state": final_state,
            }

        except Exception as e:
            self.logger.error(f"❌ Pipeline 실행 실패: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "pipeline_id": input_data.get("pipeline_id", "unknown"),
            }

    def _calculate_processing_time(self, final_state: Dict[str, Any]) -> float:
        """처리 시간 계산"""
        try:
            from datetime import datetime

            start_time = datetime.fromisoformat(final_state["started_at"])
            end_time = datetime.fromisoformat(
                final_state.get("completed_at", datetime.now().isoformat())
            )
            return (end_time - start_time).total_seconds()
        except:
            return 0.0
