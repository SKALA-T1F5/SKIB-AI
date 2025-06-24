from typing import List, Dict, Any
from src.agents.trainee_assistant.models import ChatMessage, MessageType
from datetime import datetime

class ConversationMemoryManager:
    """대화 메모리 관리 클래스"""
    
    def __init__(self, max_context_messages: int = 20):
        self.max_context_messages = max_context_messages
        self.conversation_history: List[ChatMessage] = []
    
    def add_message(self, message_type: MessageType, content: str, metadata: Dict[str, Any] = None):
        """대화 히스토리에 메시지 추가"""
        message = ChatMessage(
            type=message_type,
            content=content,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )
        self.conversation_history.append(message)
        self._manage_memory()
    
    def _manage_memory(self):
        """메모리 관리: 최대 메시지 수 초과 시 오래된 메시지 제거"""
        if len(self.conversation_history) > self.max_context_messages:
            # 시스템 메시지는 유지하고 사용자-어시스턴트 메시지만 관리
            system_messages = [msg for msg in self.conversation_history if msg.type == MessageType.SYSTEM]
            other_messages = [msg for msg in self.conversation_history if msg.type != MessageType.SYSTEM]
            
            # 최근 메시지들만 유지
            recent_messages = other_messages[-(self.max_context_messages - len(system_messages)):]
            
            self.conversation_history = system_messages + recent_messages
    
    def get_recent_chat_messages(self, count: int = 6) -> List[ChatMessage]:
        """최근 채팅 메시지 반환 (도구 호출 메시지 제외)"""
        chat_messages = [
            msg for msg in self.conversation_history 
            if msg.type in [MessageType.USER, MessageType.ASSISTANT]
        ]
        return chat_messages[-count:]
    
    def get_tool_calls_count(self) -> int:
        """도구 호출 횟수 반환"""
        return len([msg for msg in self.conversation_history if msg.type == MessageType.TOOL_CALL])
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """대화 요약 정보 반환"""
        tool_calls = [msg for msg in self.conversation_history if msg.type == MessageType.TOOL_CALL]
        
        return {
            "total_messages": len(self.conversation_history),
            "tool_calls": len(tool_calls),
            "last_message_time": self.conversation_history[-1].timestamp.isoformat() if self.conversation_history else None
        }