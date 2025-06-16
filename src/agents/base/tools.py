from typing import Dict, Any, Optional
import os
import asyncio
from abc import ABC, abstractmethod


class BaseTool(ABC):
    """
    모든 도구의 기본 추상 클래스
    
    Tools는 순수 기능을 제공하며:
    - 입력 → 처리 → 출력의 단방향 흐름
    - State를 보유하지 않음
    - 여러 Agent에서 재사용 가능
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """도구 초기화"""
        self.config = config or {}
        self._initialized = False
    
    async def initialize(self) -> None:
        """도구 초기화 (필요시 하위 클래스에서 구현)"""
        self._initialized = True
    
    @abstractmethod
    async def execute(self, *args, **kwargs) -> Any:
        """도구의 메인 실행 메서드 (하위 클래스에서 구현)"""
        pass
    
    def is_initialized(self) -> bool:
        """초기화 상태 확인"""
        return self._initialized