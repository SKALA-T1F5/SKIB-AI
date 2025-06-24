from abc import ABC, abstractmethod
from typing import List, Dict, Any
import re
from src.agents.trainee_assistant.models import SearchResult

def normalize_collection_name(name: str) -> str:
    """컬렉션명 정규화 (소문자 + 알파벳/숫자/언더스코어만 허용)"""
    return re.sub(r'[^a-zA-Z0-9_]', '_', name.strip().lower())

class BaseTool(ABC):
    @abstractmethod
    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        pass