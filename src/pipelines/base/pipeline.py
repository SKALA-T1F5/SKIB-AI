"""
BasePipeline - Agent 협업을 조정하는 기본 Pipeline 클래스

Pipeline은 여러 Agent들의 워크플로우를 관리하고,
공유 상태를 통해 Agent 간 데이터 교환을 담당합니다.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Type, Callable
from datetime import datetime
import asyncio
import logging

from src.agents.base.agent import BaseAgent
from src.agents.base.state import BaseState, StateStatus, update_state_progress, add_state_log, add_state_error


class PipelineStep:
    """Pipeline의 단일 스텝을 나타내는 클래스"""
    
    def __init__(
        self,
        name: str,
        agent: BaseAgent,
        condition: Optional[Callable[[BaseState], bool]] = None,
        retry_count: int = 3,
        timeout: Optional[float] = None
    ):
        """
        Pipeline 스텝 초기화
        
        Args:
            name: 스텝 이름
            agent: 실행할 Agent
            condition: 스텝 실행 조건 (선택적)
            retry_count: 재시도 횟수
            timeout: 타임아웃 (초)
        """
        self.name = name
        self.agent = agent
        self.condition = condition
        self.retry_count = retry_count
        self.timeout = timeout
    
    async def should_execute(self, state: BaseState) -> bool:
        """스텝을 실행해야 하는지 확인"""
        if self.condition is None:
            return True
        return self.condition(state)
    
    async def execute(self, input_data: Dict[str, Any], state: BaseState) -> BaseState:
        """스텝 실행"""
        if self.timeout:
            return await asyncio.wait_for(
                self.agent.execute(input_data, state),
                timeout=self.timeout
            )
        else:
            return await self.agent.execute(input_data, state)


class BasePipeline(ABC):
    """
    모든 Pipeline의 기본 추상 클래스
    
    Pipeline은 다음과 같은 책임을 가집니다:
    - Agent 간 워크플로우 조정
    - 공유 상태 관리
    - 에러 처리 및 복구
    - 병렬/순차 실행 제어
    """
    
    def __init__(
        self,
        name: str,
        state_class: Type[BaseState] = BaseState,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Pipeline 초기화
        
        Args:
            name: Pipeline 이름
            state_class: 사용할 공유 State 클래스
            config: Pipeline 설정
        """
        self.name = name
        self.state_class = state_class
        self.config = config or {}
        self.logger = logging.getLogger(f"pipeline.{name}")
        
        # Pipeline 구성 요소
        self.steps: List[PipelineStep] = []
        self.agents: Dict[str, BaseAgent] = {}
        self.parallel_groups: Dict[str, List[str]] = {}
        
        # Pipeline 상태
        self._initialized = False
        self._shared_state: Optional[BaseState] = None
        
    async def initialize(self) -> None:
        """Pipeline 초기화"""
        if self._initialized:
            return
        
        try:
            # 스텝들 구성
            await self._setup_steps()
            
            # Agent들 초기화
            for agent in self.agents.values():
                await agent.initialize()
            
            self._initialized = True
            self.logger.info(f"Pipeline {self.name} initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize pipeline {self.name}: {e}")
            raise
    
    async def execute(self, input_data: Dict[str, Any]) -> BaseState:
        """
        Pipeline 메인 실행 메서드
        
        Args:
            input_data: 입력 데이터
            
        Returns:
            최종 공유 상태
        """
        if not self._initialized:
            await self.initialize()
        
        # 공유 상태 초기화
        self._shared_state = self._create_initial_shared_state(input_data)
        
        update_state_progress(
            self._shared_state,
            progress=0.0,
            current_agent=self.name,
            status=StateStatus.PROCESSING
        )
        
        try:
            self.logger.info(f"Starting pipeline execution: {self.name}")
            
            # Pipeline 워크플로우 실행
            result = await self._execute_workflow(input_data)
            
            # 성공 시 상태 업데이트
            update_state_progress(
                self._shared_state,
                progress=1.0,
                status=StateStatus.COMPLETED
            )
            
            add_state_log(
                self._shared_state,
                level="INFO",
                message=f"Pipeline {self.name} completed successfully",
                agent=self.name
            )
            
            return self._shared_state
            
        except Exception as e:
            self.logger.error(f"Pipeline {self.name} execution failed: {e}")
            
            add_state_error(
                self._shared_state,
                error_type=type(e).__name__,
                error_message=str(e),
                agent=self.name
            )
            
            raise
    
    async def _execute_workflow(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Pipeline 워크플로우 실행 (순차 + 병렬 처리)"""
        
        total_steps = len(self.steps)
        completed_steps = 0
        
        # 병렬 실행 그룹 추적
        parallel_tasks = {}
        
        for step in self.steps:
            try:
                # 스텝 실행 조건 확인
                if not await step.should_execute(self._shared_state):
                    self.logger.info(f"Skipping step {step.name} due to condition")
                    completed_steps += 1
                    continue
                
                self.logger.info(f"Executing step: {step.name}")
                
                # 병렬 그룹 확인
                parallel_group = self._get_parallel_group(step.name)
                
                if parallel_group:
                    # 병렬 실행
                    if parallel_group not in parallel_tasks:
                        parallel_tasks[parallel_group] = []
                    
                    task = asyncio.create_task(
                        self._execute_step_with_retry(step, input_data)
                    )
                    parallel_tasks[parallel_group].append(task)
                    
                else:
                    # 순차 실행
                    await self._execute_step_with_retry(step, input_data)
                    completed_steps += 1
                    
                    # 진행률 업데이트
                    progress = completed_steps / total_steps
                    update_state_progress(self._shared_state, progress)
            
            except Exception as e:
                self.logger.error(f"Step {step.name} failed: {e}")
                raise
        
        # 병렬 작업들 완료 대기
        for group_name, tasks in parallel_tasks.items():
            self.logger.info(f"Waiting for parallel group: {group_name}")
            await asyncio.gather(*tasks)
            completed_steps += len(tasks)
            
            progress = completed_steps / total_steps
            update_state_progress(self._shared_state, progress)
        
        return {"status": "completed", "shared_state": self._shared_state}
    
    async def _execute_step_with_retry(
        self,
        step: PipelineStep,
        input_data: Dict[str, Any]
    ) -> BaseState:
        """재시도 로직을 포함한 스텝 실행"""
        
        last_exception = None
        
        for attempt in range(step.retry_count + 1):
            try:
                add_state_log(
                    self._shared_state,
                    level="DEBUG",
                    message=f"Executing step {step.name}, attempt {attempt + 1}",
                    agent=step.agent.name
                )
                
                # 스텝 실행
                result_state = await step.execute(input_data, self._shared_state)
                
                # 공유 상태 업데이트
                self._merge_states(result_state)
                
                add_state_log(
                    self._shared_state,
                    level="INFO",
                    message=f"Step {step.name} completed successfully",
                    agent=step.agent.name
                )
                
                return self._shared_state
                
            except Exception as e:
                last_exception = e
                self.logger.warning(f"Step {step.name} attempt {attempt + 1} failed: {e}")
                
                if attempt < step.retry_count:
                    # 재시도 전 대기 (지수 백오프)
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                else:
                    # 최대 재시도 횟수 도달
                    add_state_error(
                        self._shared_state,
                        error_type=type(e).__name__,
                        error_message=f"Step {step.name} failed after {step.retry_count} retries: {str(e)}",
                        agent=step.agent.name
                    )
                    raise
        
        # 여기에 도달하면 안 되지만, 안전장치
        if last_exception:
            raise last_exception
        else:
            raise RuntimeError(f"Step {step.name} failed unexpectedly")
    
    def _merge_states(self, agent_state: BaseState) -> None:
        """Agent 상태를 공유 상태로 병합"""
        
        # 기본 필드들 업데이트
        self._shared_state["updated_at"] = agent_state.get("updated_at", datetime.now())
        
        # 에러 및 로그 병합
        if "errors" in agent_state:
            if "errors" not in self._shared_state:
                self._shared_state["errors"] = []
            self._shared_state["errors"].extend(agent_state["errors"])
        
        if "warnings" in agent_state:
            if "warnings" not in self._shared_state:
                self._shared_state["warnings"] = []
            self._shared_state["warnings"].extend(agent_state["warnings"])
        
        if "logs" in agent_state:
            if "logs" not in self._shared_state:
                self._shared_state["logs"] = []
            self._shared_state["logs"].extend(agent_state["logs"])
        
        # 메시지 병합
        if "messages" in agent_state:
            if "messages" not in self._shared_state:
                self._shared_state["messages"] = []
            self._shared_state["messages"].extend(agent_state["messages"])
        
        # 컨텍스트 병합
        if "context" in agent_state:
            if "context" not in self._shared_state:
                self._shared_state["context"] = {}
            self._shared_state["context"].update(agent_state["context"])
        
        # 중간 결과 병합
        if "intermediate_results" in agent_state:
            if "intermediate_results" not in self._shared_state:
                self._shared_state["intermediate_results"] = {}
            self._shared_state["intermediate_results"].update(agent_state["intermediate_results"])
        
        # Agent별 특화 필드들 병합 (하위 클래스에서 오버라이드)
        self._merge_specialized_fields(agent_state)
    
    def _merge_specialized_fields(self, agent_state: BaseState) -> None:
        """특화된 필드들을 병합 (하위 클래스에서 구현)"""
        pass
    
    def _get_parallel_group(self, step_name: str) -> Optional[str]:
        """스텝이 속한 병렬 그룹을 찾습니다"""
        for group_name, step_names in self.parallel_groups.items():
            if step_name in step_names:
                return group_name
        return None
    
    @abstractmethod
    async def _setup_steps(self) -> None:
        """Pipeline 스텝들을 설정합니다 (하위 클래스에서 구현)"""
        pass
    
    def add_step(
        self,
        name: str,
        agent: BaseAgent,
        condition: Optional[Callable[[BaseState], bool]] = None,
        retry_count: int = 3,
        timeout: Optional[float] = None
    ) -> None:
        """Pipeline에 스텝을 추가합니다"""
        
        step = PipelineStep(
            name=name,
            agent=agent,
            condition=condition,
            retry_count=retry_count,
            timeout=timeout
        )
        
        self.steps.append(step)
        self.agents[name] = agent
        
        self.logger.debug(f"Added step {name} to pipeline {self.name}")
    
    def add_parallel_group(self, group_name: str, step_names: List[str]) -> None:
        """병렬 실행 그룹을 추가합니다"""
        self.parallel_groups[group_name] = step_names
        self.logger.debug(f"Added parallel group {group_name} with steps: {step_names}")
    
    def _create_initial_shared_state(self, input_data: Dict[str, Any]) -> BaseState:
        """초기 공유 상태를 생성합니다"""
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
    
    def get_shared_state(self) -> Optional[BaseState]:
        """현재 공유 상태를 반환합니다"""
        return self._shared_state
    
    def get_agent(self, agent_name: str) -> Optional[BaseAgent]:
        """특정 Agent를 가져옵니다"""
        return self.agents.get(agent_name)
    
    def has_agent(self, agent_name: str) -> bool:
        """특정 Agent를 가지고 있는지 확인합니다"""
        return agent_name in self.agents
    
    async def pause(self) -> None:
        """Pipeline 실행을 일시 정지합니다"""
        if self._shared_state:
            self._shared_state["status"] = StateStatus.PAUSED
            add_state_log(
                self._shared_state,
                level="INFO",
                message=f"Pipeline {self.name} paused",
                agent=self.name
            )
    
    async def resume(self) -> None:
        """Pipeline 실행을 재개합니다"""
        if self._shared_state:
            self._shared_state["status"] = StateStatus.PROCESSING
            add_state_log(
                self._shared_state,
                level="INFO",
                message=f"Pipeline {self.name} resumed",
                agent=self.name
            )
    
    def __str__(self) -> str:
        return f"Pipeline({self.name})"
    
    def __repr__(self) -> str:
        return f"Pipeline(name={self.name}, steps={len(self.steps)}, agents={list(self.agents.keys())}, initialized={self._initialized})"


class MockPipeline(BasePipeline):
    """
    테스트용 Mock Pipeline
    실제 Pipeline 구현의 예시이기도 합니다
    """
    
    async def _setup_steps(self) -> None:
        """Mock 스텝들을 설정합니다"""
        from src.agents.base.agent import MockAgent
        
        # Mock Agent들 생성
        agent1 = MockAgent("mock_agent_1")
        agent2 = MockAgent("mock_agent_2")
        agent3 = MockAgent("mock_agent_3")
        
        # 순차 스텝들 추가
        self.add_step("step1", agent1)
        self.add_step("step2", agent2)
        self.add_step("step3", agent3)
        
        # 병렬 그룹 예시 (step2와 step3를 병렬 실행)
        # self.add_parallel_group("parallel_group_1", ["step2", "step3"])


# Pipeline 실행을 위한 유틸리티 함수들
async def run_pipeline_with_timeout(
    pipeline: BasePipeline,
    input_data: Dict[str, Any],
    timeout: float
) -> BaseState:
    """타임아웃과 함께 Pipeline을 실행합니다"""
    try:
        return await asyncio.wait_for(
            pipeline.execute(input_data),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        await pipeline.pause()
        raise TimeoutError(f"Pipeline {pipeline.name} timed out after {timeout} seconds")


def create_conditional_step(
    condition_func: Callable[[BaseState], bool]
) -> Callable[[BaseState], bool]:
    """조건부 스텝 실행을 위한 데코레이터"""
    return condition_func


# 조건부 실행 헬퍼 함수들
def has_errors(state: BaseState) -> bool:
    """상태에 에러가 있는지 확인"""
    return bool(state.get("errors", []))


def has_data(state: BaseState, key: str) -> bool:
    """상태에 특정 키의 데이터가 있는지 확인"""
    return key in state.get("context", {}) or key in state.get("intermediate_results", {})


def progress_greater_than(threshold: float) -> Callable[[BaseState], bool]:
    """진행률이 임계값보다 큰지 확인하는 조건 함수"""
    def condition(state: BaseState) -> bool:
        return state.get("progress", 0.0) > threshold
    return conditio