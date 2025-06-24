from typing import Dict, Any, List
from src.agents.trainee_assistant.agent import TraineeAssistantAgent
import asyncio

class TraineeAssistantPipeline:
    """
    시험 후 학습 지원을 위한 Trainee Assistant 파이프라인
    세션별로 독립된 에이전트 인스턴스를 관리
    """
    
    def __init__(self):
        self.active_sessions: Dict[str, TraineeAssistantAgent] = {}
    
    def get_or_create_session(self, session_id: str) -> TraineeAssistantAgent:
        """세션 ID 기준으로 Agent 인스턴스를 가져오거나 새로 생성"""
        if session_id not in self.active_sessions:
            self.active_sessions[session_id] = TraineeAssistantAgent()
        return self.active_sessions[session_id]
    
    async def process_chat_message(
        self, 
        session_id: str, 
        user_message: str, 
        question_context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """사용자 메시지를 처리하고 어시스턴트 응답을 반환"""
        
        agent = self.get_or_create_session(session_id)
        
        # 문제 컨텍스트가 제공된 경우 설정
        if question_context:
            agent.set_question_context(question_context)
        
        # RAG 파이프라인으로 메시지 처리
        result = await agent.process_message(user_message)
        
        return {
            "response": result["response"],
            "session_info": agent.get_conversation_summary()
        }
    
    async def process_enhanced_chat_message(
        self, 
        session_id: str, 
        user_message: str, 
        question_context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """강화된 채팅 메시지 처리 - 워크플로우 정보 포함"""
        
        agent = self.get_or_create_session(session_id)
        
        # 문제 컨텍스트가 제공된 경우 설정
        if question_context:
            agent.set_question_context(question_context)
        
        # RAG 파이프라인으로 메시지 처리
        result = await agent.process_message(user_message)
        
        return {
            "response": result["response"],
            "workflow_info": result["workflow_info"],
            "session_info": agent.get_conversation_summary()
        }

    def cleanup_session(self, session_id: str):
        """세션 종료 및 자원 정리"""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
    
    def get_active_sessions_count(self) -> int:
        """현재 활성화된 세션 수 반환"""
        return len(self.active_sessions)