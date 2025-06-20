"""
Agent 관련 예외 클래스들
"""

from typing import Any, Dict, Optional

from .base_exceptions import SKIBBaseException


class AgentException(SKIBBaseException):
    """Agent 관련 기본 예외"""

    def __init__(
        self,
        message: str,
        agent_name: Optional[str] = None,
        agent_state: Optional[Dict[str, Any]] = None,
        details: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        super().__init__(message, details=details, **kwargs)

        if agent_name:
            self.details["agent_name"] = agent_name
        if agent_state:
            self.details["agent_state"] = agent_state


class AgentInitializationError(AgentException):
    """Agent 초기화 오류"""


class AgentExecutionError(AgentException):
    """Agent 실행 오류"""


class AgentValidationError(AgentException):
    """Agent 검증 오류"""


class AgentToolError(AgentException):
    """Agent 도구 관련 오류"""

    def __init__(
        self,
        message: str,
        tool_name: Optional[str] = None,
        tool_error: Optional[Exception] = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)

        if tool_name:
            self.details["tool_name"] = tool_name
        if tool_error:
            self.details["tool_error"] = str(tool_error)
            self.cause = tool_error


class AgentTimeoutError(AgentException):
    """Agent 타임아웃 오류"""


class AgentStateError(AgentException):
    """Agent 상태 관련 오류"""


# Agent 예외 생성 헬퍼 함수들
def create_agent_initialization_error(
    agent_name: str, reason: str, missing_dependencies: Optional[list] = None
) -> AgentInitializationError:
    """Agent 초기화 오류 생성"""
    details = {"initialization_reason": reason}
    if missing_dependencies:
        details["missing_dependencies"] = ", ".join(
            str(dep) for dep in missing_dependencies
        )

    return AgentInitializationError(
        message=f"Failed to initialize agent '{agent_name}': {reason}",
        error_code="AGENT_INIT_ERROR",
        agent_name=agent_name,
        details=details,
    )


def create_agent_execution_error(
    agent_name: str,
    operation: str,
    reason: str,
    input_data: Optional[Dict[str, Any]] = None,
) -> AgentExecutionError:
    """Agent 실행 오류 생성"""
    details = {"operation": operation, "execution_reason": reason}
    if input_data:
        details["input_data"] = str(input_data)

    return AgentExecutionError(
        message=f"Agent '{agent_name}' failed during {operation}: {reason}",
        error_code="AGENT_EXEC_ERROR",
        agent_name=agent_name,
        details=details,
    )


def create_agent_validation_error(
    agent_name: str,
    validation_type: str,
    failed_criteria: str,
    result_data: Optional[Dict[str, Any]] = None,
) -> AgentValidationError:
    """Agent 검증 오류 생성"""
    details = {"validation_type": validation_type, "failed_criteria": failed_criteria}
    if result_data:
        details["result_data"] = str(result_data)

    return AgentValidationError(
        message=f"Agent '{agent_name}' validation failed ({validation_type}): {failed_criteria}",
        error_code="AGENT_VALIDATION_ERROR",
        agent_name=agent_name,
        details=details,
    )


def create_agent_tool_error(
    agent_name: str, tool_name: str, tool_operation: str, tool_error: Exception
) -> AgentToolError:
    """Agent 도구 오류 생성"""
    return AgentToolError(
        message=f"Tool '{tool_name}' failed in agent '{agent_name}' during {tool_operation}",
        error_code="AGENT_TOOL_ERROR",
        agent_name=agent_name,
        tool_name=tool_name,
        tool_error=tool_error,
        details={"tool_operation": tool_operation},
    )
