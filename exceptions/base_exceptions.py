"""
SKIB-AI 시스템의 기본 예외 클래스들

모든 커스텀 예외는 이 기본 예외들을 상속받아 구현합니다.
"""

from datetime import datetime
from typing import Any, Dict, Optional


class SKIBBaseException(Exception):
    """
    SKIB-AI 시스템의 모든 예외의 기본 클래스
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        """
        기본 예외 초기화

        Args:
            message: 에러 메시지
            error_code: 에러 코드 (로깅/모니터링용)
            details: 추가 세부 정보
            cause: 원인이 된 예외
        """
        super().__init__(message)

        self.message = message
        self.error_code = error_code or self.__class__.__name__.upper()
        self.details = details or {}
        self.cause = cause
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """예외를 딕셔너리로 변환"""
        return {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "cause": str(self.cause) if self.cause else None,
        }

    def __str__(self) -> str:
        return f"[{self.error_code}] {self.message}"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(message={self.message!r}, error_code={self.error_code!r})"


class SKIBConfigurationError(SKIBBaseException):
    """설정 관련 오류"""


class SKIBValidationError(SKIBBaseException):
    """데이터 검증 오류"""


class SKIBTimeoutError(SKIBBaseException):
    """타임아웃 오류"""


class SKIBResourceError(SKIBBaseException):
    """리소스 관련 오류 (메모리, 파일 등)"""


class SKIBNetworkError(SKIBBaseException):
    """네트워크 관련 오류"""


class SKIBAuthenticationError(SKIBBaseException):
    """인증 관련 오류"""


class SKIBPermissionError(SKIBBaseException):
    """권한 관련 오류"""


# 예외 생성 헬퍼 함수들
def create_configuration_error(
    message: str, config_key: Optional[str] = None, config_value: Optional[Any] = None
) -> SKIBConfigurationError:
    """설정 오류 생성 헬퍼"""
    details = {}
    if config_key:
        details["config_key"] = config_key
    if config_value is not None:
        details["config_value"] = str(config_value)

    return SKIBConfigurationError(
        message=message, error_code="CONFIG_ERROR", details=details
    )


def create_validation_error(
    message: str,
    field_name: Optional[str] = None,
    field_value: Optional[Any] = None,
    expected_type: Optional[str] = None,
) -> SKIBValidationError:
    """검증 오류 생성 헬퍼"""
    details = {}
    if field_name:
        details["field_name"] = field_name
    if field_value is not None:
        details["field_value"] = str(field_value)
    if expected_type:
        details["expected_type"] = expected_type

    return SKIBValidationError(
        message=message, error_code="VALIDATION_ERROR", details=details
    )


def create_timeout_error(
    message: str,
    operation: Optional[str] = None,
    timeout_duration: Optional[float] = None,
) -> SKIBTimeoutError:
    """타임아웃 오류 생성 헬퍼"""
    details = {}
    if operation:
        details["operation"] = operation
    if timeout_duration:
        details["timeout_duration"] = timeout_duration

    return SKIBTimeoutError(
        message=message, error_code="TIMEOUT_ERROR", details=details
    )


def create_resource_error(
    message: str,
    resource_type: Optional[str] = None,
    resource_path: Optional[str] = None,
) -> SKIBResourceError:
    """리소스 오류 생성 헬퍼"""
    details = {}
    if resource_type:
        details["resource_type"] = resource_type
    if resource_path:
        details["resource_path"] = resource_path

    return SKIBResourceError(
        message=message, error_code="RESOURCE_ERROR", details=details
    )
