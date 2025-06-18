class PipelineException(Exception):
    """Pipeline 기본 예외"""
    def __init__(self, message: str, pipeline_name: str, step: str = ""):
        super().__init__(f"[{pipeline_name}:{step}] {message}")
        self.message = message
        self.pipeline_name = pipeline_name
        self.step = step


class PipelineTimeoutException(PipelineException):
    """Pipeline 타임아웃 예외"""
    pass


class PipelineValidationException(PipelineException):
    """Pipeline 입력 검증 예외"""
    pass
