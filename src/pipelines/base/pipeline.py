# src/pipelines/base/pipeline.py
from typing import Dict, Any, Optional, Callable, List
from abc import ABC, abstractmethod
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
import logging
import uuid


class BasePipeline(ABC):
    """LangGraph 기반 Pipeline 추상 클래스"""
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        checkpointer: Optional[Any] = None,
        logger: Optional[logging.Logger] = None
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
        logger.setLevel(logging.INFO)
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
            "total_steps": len(self._get_node_list())
        }
    
    def _build_and_compile(self):
        """워크플로우 빌드 및 컴파일"""
        self.workflow = self._build_workflow()
        self.compiled_graph = self.workflow.compile(
            checkpointer=self.checkpointer
        )
    
    @abstractmethod
    def _build_workflow(self) -> StateGraph:
        """워크플로우 구성 (하위 클래스에서 구현)"""
        pass
    
    @abstractmethod 
    def _get_node_list(self) -> List[str]:
        """노드 목록 반환 (진행률 계산용)"""
        pass
    
    @abstractmethod
    def _get_state_schema(self) -> type:
        """Pipeline별 상태 스키마 반환"""
        pass
    
    # 실행 관련 메서드
    async def run(
        self, 
        input_data: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Pipeline 실행"""
        pass
    
    async def stream(
        self,
        input_data: Dict[str, Any],
        session_id: Optional[str] = None
    ):
        """Pipeline 스트리밍 실행"""
        pass
    
    # 상태 관리 메서드
    def _update_progress(self, current_step: str, state: Dict[str, Any]) -> Dict[str, Any]:
        """진행률 업데이트"""
        pass
    
    def _handle_error(self, error: Exception, state: Dict[str, Any]) -> Dict[str, Any]:
        """에러 처리"""
        pass
    
    # 유틸리티 메서드
    def _create_node_wrapper(self, node_func: Callable) -> Callable:
        """노드 함수 래퍼 (에러 처리, 로깅 등)"""
        pass
    
    def _should_retry(self, state: Dict[str, Any]) -> bool:
        """재시도 여부 판단"""
        pass