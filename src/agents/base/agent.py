"""
BaseAgent - 모든 Agent의 기본 추상 클래스

목표 지향적 Agent의 공통 인터페이스를 정의합니다.
각 Agent는 이 클래스를 상속받아 구체적인 로직을 구현해야 합니다.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Type
from datetime import datetime
import asyncio
import logging

from .state import BaseState, StateStatus, update_state_progress, add_state_log, add_state_error


class BaseAgent(ABC):
    """
    모든 Agent의 기본 추상 클래스
    
    Agent는 목표 지향적이며 다음과 같은 특징을 가집니다:
    - 자체 State 관리
    - 판단 및 전략 수행
    - Tools를 활용한 작업 실행
    - 결과 검증 및 재시도
    """
    
    def __init__(
        self,
        name: str,
        state_class: Type[BaseState] = BaseState,
        tools: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Agent 초기화
        
        Args:
            name: Agent 이름
            state_class: 사용할 State 클래스
            tools: Agent가 사용할 도구들
            config: Agent 설정
        """
        self.name = name
        self.state_class = state_class
        self.tools = tools or {}
        self.config = config or {}
        self.logger = logging.getLogger(f"agent.{name}")
        
        # Agent 상태
        self._initialized = False
        self._current_state: Optional[BaseState] = None
        
    async def initialize(self) -> None:
        """Agent 초기화 (비동기)"""
        if self._initialized:
            return
            
        try:
            await self._setup_tools()
            await self._load_config()
            self._initialized = True
            self.logger.info(f"Agent {self.name} initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize agent {self.name}: {e}")
            raise
    
    async def execute(
        self,
        input_data: Dict[str, Any],
        shared_state: Optional[BaseState] = None
    ) -> BaseState:
        """
        Agent의 메인 실행 메서드
        
        Args:
            input_data: 입력 데이터
            shared_state: 공유 상태 (Pipeline에서 전달)
            
        Returns:
            업데이트된 상태
        """
        if not self._initialized:
            await self.initialize()
        
        # 상태 초기화 또는 업데이트
        if shared_state:
            self._current_state = shared_state
        else:
            self._current_state = self._create_initial_state(input_data)
        
        # 진행 상황 업데이트
        update_state_progress(
            self._current_state,
            progress=0.0,
            current_agent=self.name,
            status=StateStatus.PROCESSING
        )
        
        try:
            self.logger.info(f"Starting execution for agent {self.name}")
            
            # Agent 실행 플로우
            result = await self._execute_workflow(input_data)
            
            # 성공 시 상태 업데이트
            update_state_progress(
                self._current_state,
                progress=1.0,
                status=StateStatus.COMPLETED
            )
            
            add_state_log(
                self._current_state,
                level="INFO",
                message=f"Agent {self.name} completed successfully",
                agent=self.name
            )
            
            return self._current_state
            
        except Exception as e:
            self.logger.error(f"Agent {self.name} execution failed: {e}")
            
            add_state_error(
                self._current_state,
                error_type=type(e).__name__,
                error_message=str(e),
                agent=self.name
            )
            
            raise
    
    async def _execute_workflow(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Agent의 핵심 워크플로우 실행
        
        이 메서드는 Agent의 표준 실행 패턴을 구현합니다:
        1. Plan (계획 수립)
        2. Act (실행)
        3. Reflect (검토)
        4. Retry (필요시 재시도)
        """
        max_retries = self.config.get("max_retries", 3)
        
        for attempt in range(max_retries + 1):
            try:
                # 1. 계획 수립
                plan = await self.plan(input_data, self._current_state)
                add_state_log(
                    self._current_state,
                    level="DEBUG",
                    message=f"Plan created: {plan}",
                    agent=self.name
                )
                
                # 2. 실행
                result = await self.act(plan, self._current_state)
                update_state_progress(self._current_state, 0.7)
                
                # 3. 검토
                is_valid, feedback = await self.reflect(result, self._current_state)
                update_state_progress(self._current_state, 0.9)
                
                if is_valid:
                    self.logger.info(f"Agent {self.name} completed successfully on attempt {attempt + 1}")
                    # 결과를 상태의 output 필드에 저장
                    self._current_state["output"] = result
                    return result
                else:
                    self.logger.warning(f"Agent {self.name} validation failed on attempt {attempt + 1}: {feedback}")
                    if attempt < max_retries:
                        await asyncio.sleep(1)  # 재시도 전 대기
                        continue
                    else:
                        raise ValueError(f"Agent failed validation after {max_retries} attempts: {feedback}")
                        
            except Exception as e:
                if attempt < max_retries:
                    self.logger.warning(f"Agent {self.name} attempt {attempt + 1} failed: {e}. Retrying...")
                    await asyncio.sleep(2 ** attempt)  # 지수 백오프
                else:
                    raise
        
        raise RuntimeError(f"Agent {self.name} failed after {max_retries} retries")
    
    @abstractmethod
    async def plan(self, input_data: Dict[str, Any], state: BaseState) -> Dict[str, Any]:
        """
        작업 계획을 수립합니다
        
        Args:
            input_data: 입력 데이터
            state: 현재 상태
            
        Returns:
            실행 계획
        """
        pass
    
    @abstractmethod
    async def act(self, plan: Dict[str, Any], state: BaseState) -> Dict[str, Any]:
        """
        계획에 따라 실제 작업을 수행합니다
        
        Args:
            plan: 실행 계획
            state: 현재 상태
            
        Returns:
            실행 결과
        """
        pass
    
    @abstractmethod
    async def reflect(self, result: Dict[str, Any], state: BaseState) -> tuple[bool, str]:
        """
        실행 결과를 검토하고 유효성을 검증합니다
        
        Args:
            result: 실행 결과
            state: 현재 상태
            
        Returns:
            (is_valid, feedback) 튜플
        """
        pass
    
    async def _setup_tools(self) -> None:
        """도구들을 설정합니다 (하위 클래스에서 오버라이드)"""
        pass
    
    async def _load_config(self) -> None:
        """설정을 로드합니다 (하위 클래스에서 오버라이드)"""
        pass
    
    def _create_initial_state(self, input_data: Dict[str, Any]) -> BaseState:
        """초기 상태를 생성합니다"""
        from uuid import uuid4
        
        return self.state_class(
            session_id=input_data.get("session_id", str(uuid4())),
            request_id=input_data.get("request_id", str(uuid4())),
            user_id=input_data.get("user_id"),
            created_at=datetime.now(),
            updated_at=datetime.now(),
            status=StateStatus.PENDING,
            current_agent=self.name,
            progress=0.0,
            errors=[],
            warnings=[],
            logs=[],
            messages=[],
            context=input_data.get("context", {}),
            intermediate_results={}
        )
    
    def get_current_state(self) -> Optional[BaseState]:
        """현재 상태를 반환합니다"""
        return self._current_state
    
    def update_progress(self, progress: float, message: Optional[str] = None) -> None:
        """진행 상황을 업데이트합니다"""
        if self._current_state:
            update_state_progress(self._current_state, progress, current_agent=self.name)
            if message:
                add_state_log(
                    self._current_state,
                    level="INFO",
                    message=message,
                    agent=self.name
                )
    
    def add_warning(self, message: str) -> None:
        """경고를 추가합니다"""
        if self._current_state:
            if "warnings" not in self._current_state:
                self._current_state["warnings"] = []
            self._current_state["warnings"].append(message)
            
            add_state_log(
                self._current_state,
                level="WARNING",
                message=message,
                agent=self.name
            )
    
    def get_tool(self, tool_name: str) -> Optional[Any]:
        """특정 도구를 가져옵니다"""
        return self.tools.get(tool_name)
    
    def has_tool(self, tool_name: str) -> bool:
        """특정 도구를 가지고 있는지 확인합니다"""
        return tool_name in self.tools
    
    def __str__(self) -> str:
        return f"Agent({self.name})"
    
    def __repr__(self) -> str:
        return f"Agent(name={self.name}, tools={list(self.tools.keys())}, initialized={self._initialized})"


class MockAgent(BaseAgent):
    """
    테스트용 Mock Agent
    실제 Agent 구현의 예시이기도 합니다
    """
    
    async def plan(self, input_data: Dict[str, Any], state: BaseState) -> Dict[str, Any]:
        return {
            "action": "mock_action",
            "parameters": input_data,
            "estimated_duration": 1.0
        }
    
    async def act(self, plan: Dict[str, Any], state: BaseState) -> Dict[str, Any]:
        # Mock 실행 (실제로는 1초 대기)
        await asyncio.sleep(1)
        
        return {
            "status": "completed",
            "result": f"Mock result from {self.name}",
            "execution_time": 1.0
        }
    
    async def reflect(self, result: Dict[str, Any], state: BaseState) -> tuple[bool, str]:
        # 간단한 검증
        is_valid = result.get("status") == "completed"
        feedback = "Mock validation successful" if is_valid else "Mock validation failed"
        
        return is_valid, feedback