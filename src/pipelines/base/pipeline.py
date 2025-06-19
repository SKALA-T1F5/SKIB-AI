# src/pipelines/base/pipeline.py
import logging
import time
import uuid
from abc import ABC, abstractmethod
from typing import Any, Awaitable, Callable, Dict, Generic, List, Optional, TypeVar

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from src.pipelines.base.state import BasePipelineState

StateType = TypeVar("StateType", bound=BasePipelineState)


class BasePipeline(ABC, Generic[StateType]):
    """LangGraph 기반 Pipeline 추상 클래스"""

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        checkpointer: Optional[Any] = None,
        logger: Optional[logging.Logger] = None,
    ):
        self.config = config or {}

        # LangGraph 핵심 구성요소
        self.checkpointer = checkpointer or MemorySaver()
        self.workflow: Optional[StateGraph] = None
        self.compiled_graph = None

        # Pipeline 메타데이터
        self.pipeline_name = self.__class__.__name__
        self.max_retries = self.config.get("max_retries", 3)
        self.timeout_seconds = self.config.get("timeout_seconds", 300)

        # 기본 설정
        self.logger = logger or self._setup_default_logger()

        # 상태 관리
        self.default_state = self._get_default_state()

        # 워크플로우 빌드
        self._build_and_compile()

    def _setup_default_logger(self) -> logging.Logger:
        """기본 로거 설정"""
        logger = logging.getLogger(self.pipeline_name)
        logger.setLevel(logging.DEBUG)
        return logger

    def _get_default_state(self) -> Dict[str, Any]:
        """기본 상태 반환"""
        return {
            "pipeline_id": str(uuid.uuid4()),
            "current_step": "initialized",
            "processing_status": "pending",
            "progress_percentage": 0.0,
            "error_message": "",
            "retry_count": 0,
            "total_steps": len(self._get_node_list()),
        }

    def _build_and_compile(self):
        """워크플로우 빌드 및 컴파일"""
        self.workflow = self._build_workflow()
        self.compiled_graph = self.workflow.compile(checkpointer=self.checkpointer)

    @abstractmethod
    def _build_workflow(self) -> StateGraph:
        """워크플로우 구성 (하위 클래스에서 구현)"""

    @abstractmethod
    def _get_node_list(self) -> List[str]:
        """노드 목록 반환 (진행률 계산용)"""

    @abstractmethod
    def _get_state_schema(self) -> type:
        """Pipeline별 상태 스키마 반환"""

    # 실행 관련 메서드
    @abstractmethod
    async def run(
        self, input_data: Dict[str, Any], session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Pipeline 실행"""

    async def stream(
        self, input_data: Dict[str, Any], session_id: Optional[str] = None
    ):
        """Pipeline 스트리밍 실행"""

    #### Utility 메서드 ####

    def _route_next_step(self, state: StateType) -> str:
        """공통 라우팅 함수: 실패 시 에러 핸들러, 완료 시 END"""
        current_step = state.get("current_step", "")
        status = state.get("processing_status", "")
        nodes = self._get_node_list()

        if status == "failed":
            return "error_handler"
        if current_step in ["completed", "finalize"]:
            return END

        try:
            idx = nodes.index(current_step.replace("_complete", ""))
            return nodes[idx + 1] if idx + 1 < len(nodes) else END
        except ValueError:
            return END

    # 상태 관리 메서드
    def _update_progress(self, current_step: str) -> Dict[str, Any]:
        """현재 진행 상태 업데이트"""
        nodes = self._get_node_list()
        completed_steps = [
            "completed",
            "finalize",
            "vectors_skipped",
            "store_vectors_failed",
        ]
        if current_step in completed_steps:
            progress = 100
            status = "completed"
            idx = len(nodes)
        else:
            try:
                if current_step not in nodes and current_step.endswith("_complete"):
                    base = current_step.replace("_complete", "")
                    node_match = next((n for n in nodes if n.startswith(base)), None)
                    current_step = node_match if node_match else current_step
                idx = nodes.index(current_step) + 1
            except ValueError:
                idx = 0
            progress = (idx / len(nodes)) * 100 if nodes else 0
            status = "running" if progress < 100 else "completed"
        return {
            "current_step": current_step,
            "progress_percentage": progress,
            "processing_status": status,
        }

    def _handle_error(self, error: Exception, state: Dict[str, Any]) -> Dict[str, Any]:
        """에러 처리"""
        return {
            "processing_status": "failed",
            "error_message": str(error),
            "retry_count": state.get("retry_count", 0),
        }

    # 유틸리티 메서드
    def _create_node_wrapper(
        self, node_func: Callable[[StateType], Awaitable[StateType]]
    ) -> Callable[[StateType], Awaitable[StateType]]:
        """노드 함수 래퍼 (에러 처리, 로깅 등)"""

        async def wrapper(state: StateType) -> StateType:
            try:
                self.logger.debug(
                    f"Executing node: {node_func.__name__}", exc_info=True
                )
                start_time = time.time()

                result = await node_func(state)

                execution_time = time.time() - start_time
                self.logger.debug(
                    f"Node {node_func.__name__} completed in {execution_time:.2f}s",
                    exc_info=True,
                )
                # self.logger.debug(f"STATE AFTER {node_func.__name__}: {result}")

                return result

            except Exception as e:
                self.logger.error(
                    f"Node {node_func.__name__} failed: {str(e)}", exc_info=True
                )
                self.logger.debug(f"STATE ON ERROR in {node_func.__name__}: {state}")
                return self._handle_error(e, state)

        return wrapper

    def _should_retry(self, state: Dict[str, Any]) -> bool:
        """재시도 여부 판단"""
        retry_count = state.get("retry_count", 0)
        return retry_count < self.max_retries
