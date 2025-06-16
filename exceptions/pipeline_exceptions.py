"""
Pipeline 관련 예외 클래스들
"""

from typing import Optional, Dict, Any, List
from .base_exceptions import SKIBBaseException


class PipelineException(SKIBBaseException):
    """Pipeline 관련 기본 예외"""
    
    def __init__(
        self,
        message: str,
        pipeline_name: Optional[str] = None,
        pipeline_state: Optional[Dict[str, Any]] = None,
        failed_step: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        
        if pipeline_name:
            self.details["pipeline_name"] = pipeline_name
        if pipeline_state:
            self.details["pipeline_state"] = pipeline_state
        if failed_step:
            self.details["failed_step"] = failed_step


class PipelineInitializationError(PipelineException):
    """Pipeline 초기화 오류"""
    pass


class PipelineExecutionError(PipelineException):
    """Pipeline 실행 오류"""
    pass


class PipelineStepError(PipelineException):
    """Pipeline 스텝 오류"""
    
    def __init__(
        self,
        message: str,
        step_name: str,
        step_attempt: Optional[int] = None,
        step_max_retries: Optional[int] = None,
        **kwargs
    ):
        super().__init__(message, failed_step=step_name, **kwargs)
        
        if step_attempt is not None:
            self.details["step_attempt"] = step_attempt
        if step_max_retries is not None:
            self.details["step_max_retries"] = step_max_retries


class PipelineOrchestrationError(PipelineException):
    """Pipeline 협업 조정 오류"""
    pass


class PipelineStateError(PipelineException):
    """Pipeline 상태 관련 오류"""
    pass


class PipelineTimeoutError(PipelineException):
    """Pipeline 타임아웃 오류"""
    pass


class PipelineConfigurationError(PipelineException):
    """Pipeline 설정 오류"""
    pass


# Pipeline 예외 생성 헬퍼 함수들
from typing import Any

def create_pipeline_initialization_error(
    pipeline_name: str,
    reason: str,
    missing_agents: Optional[List[str]] = None,
    invalid_steps: Optional[List[str]] = None
) -> PipelineInitializationError:
    """Pipeline 초기화 오류 생성"""
    details: dict[str, Any] = {"initialization_reason": reason}
    if missing_agents:
        details["missing_agents"] = missing_agents
    if invalid_steps:
        details["invalid_steps"] = invalid_steps
    
    return PipelineInitializationError(
        message=f"Failed to initialize pipeline '{pipeline_name}': {reason}",
        error_code="PIPELINE_INIT_ERROR",
        pipeline_name=pipeline_name,
        details=details
    )


def create_pipeline_execution_error(
    pipeline_name: str,
    execution_phase: str,
    reason: str,
    completed_steps: Optional[List[str]] = None,
    remaining_steps: Optional[List[str]] = None
) -> PipelineExecutionError:
    """Pipeline 실행 오류 생성"""
    details: dict[str, Any] = {
        "execution_phase": execution_phase,
        "execution_reason": reason
    }
    if completed_steps:
        details["completed_steps"] = completed_steps
    if remaining_steps:
        details["remaining_steps"] = remaining_steps
    
    return PipelineExecutionError(
        message=f"Pipeline '{pipeline_name}' failed during {execution_phase}: {reason}",
        error_code="PIPELINE_EXEC_ERROR",
        pipeline_name=pipeline_name,
        details=details
    )


def create_pipeline_step_error(
    pipeline_name: str,
    step_name: str,
    agent_name: str,
    reason: str,
    attempt: int,
    max_retries: int,
    agent_error: Optional[Exception] = None
) -> PipelineStepError:
    """Pipeline 스텝 오류 생성"""
    details = {
        "agent_name": agent_name,
        "step_reason": reason
    }
    
    message = f"Step '{step_name}' failed in pipeline '{pipeline_name}' (attempt {attempt}/{max_retries}): {reason}"
    
    return PipelineStepError(
        message=message,
        error_code="PIPELINE_STEP_ERROR",
        pipeline_name=pipeline_name,
        step_name=step_name,
        step_attempt=attempt,
        step_max_retries=max_retries,
        cause=agent_error,
        details=details
    )


def create_pipeline_orchestration_error(
    pipeline_name: str,
    orchestration_issue: str,
    affected_agents: Optional[List[str]] = None,
    parallel_group: Optional[str] = None
) -> PipelineOrchestrationError:
    """Pipeline 협업 조정 오류 생성"""
    details: Dict[str, Any] = {"orchestration_issue": orchestration_issue}
    if affected_agents:
        details["affected_agents"] = affected_agents
    if parallel_group:
        details["parallel_group"] = parallel_group
    
    return PipelineOrchestrationError(
        message=f"Orchestration failed in pipeline '{pipeline_name}': {orchestration_issue}",
        error_code="PIPELINE_ORCHESTRATION_ERROR",
        pipeline_name=pipeline_name,
        details=details
    )


def create_pipeline_timeout_error(
    pipeline_name: str,
    timeout_duration: float,
    current_step: Optional[str] = None,
    progress: Optional[float] = None
) -> PipelineTimeoutError:
    """Pipeline 타임아웃 오류 생성"""
    details: Dict[str, Any] = {"timeout_duration": timeout_duration}
    if current_step:
        details["current_step"] = current_step
    if progress is not None:
        details["progress"] = progress
    
    return PipelineTimeoutError(
        message=f"Pipeline '{pipeline_name}' timed out after {timeout_duration} seconds",
        error_code="PIPELINE_TIMEOUT_ERROR",
        pipeline_name=pipeline_name,
        details=details
    )