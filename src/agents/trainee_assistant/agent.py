from typing import Dict, Any
from src.agents.trainee_assistant.models import MessageType
from src.agents.trainee_assistant.memory_manager import ConversationMemoryManager
from src.agents.trainee_assistant.context_manager import QuestionContextManager
from src.agents.trainee_assistant.rag_processor import RAGProcessor
from src.agents.trainee_assistant.tools import VectorSearchTool, WebSearchTool
from config.settings import settings

class TraineeAssistantAgent:
    """
    시험 후 학습 지원을 위한 Trainee Assistant AI 에이전트
    """
    
    def __init__(self, max_context_messages: int = 20, similarity_threshold: float = 0.7):
        # 각 기능별 매니저 초기화
        self.memory_manager = ConversationMemoryManager(max_context_messages)
        self.context_manager = QuestionContextManager()
        
         # 초기 도구들은 None, set_question_context 시점에 생성
        self.vector_tool = None
        self.web_tool = WebSearchTool(
            api_key=settings.google_api_key,
            cx=settings.google_cx_id
        )
        self.rag_processor = None
        self.similarity_threshold = similarity_threshold
    
    def set_question_context(self, question_data: Dict[str, Any]):
        """프론트엔드에서 받은 문제 정보를 설정하고 도구 초기화"""
        self.context_manager.set_question_context(question_data)

        # 문서명 기반으로 VectorSearchTool 구성
        document_name = question_data["document_name"]
        self.vector_tool = VectorSearchTool(document_name=document_name)
        
        # RAG Processor 구성
        self.rag_processor = RAGProcessor(
            similarity_threshold=self.similarity_threshold,
            vector_search_tool=self.vector_tool,
            web_search_tool=self.web_tool
        )
    
    async def process_message(self, user_message: str) -> Dict[str, Any]:
        """
        🟢 [1] 사용자 메시지 처리 및 RAG 파이프라인 실행
        워크플로우 정보도 함께 반환
        """
        # 사용자 메시지 추가
        self.memory_manager.add_message(MessageType.USER, user_message)
        
        # 🔵 [2] info 노드 실행
        info_result = await self.rag_processor.info_node(user_message, self.memory_manager)
        
        # 시스템 프롬프트 가져오기
        system_prompt = self.context_manager.get_system_prompt()
        
        # 다음 액션에 따라 분기
        if info_result["next_action"] == "use_vector_search":
            # 🟡 [3A] vector_search 노드 실행
            response = await self.rag_processor.vector_search_node(
                user_message, 
                info_result["results"], 
                system_prompt
            )
        else:
            # 🟡 [3B] web_search 노드 실행
            response = await self.rag_processor.web_search_node(
                user_message, 
                system_prompt, 
                self.memory_manager
            )
        
        # 어시스턴트 응답 추가
        self.memory_manager.add_message(MessageType.ASSISTANT, response)
        
        # 워크플로우 정보 포함하여 반환
        return {
            "response": response,
            "workflow_info": self.rag_processor.get_workflow_info()
        }
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """대화 요약 정보 반환"""
        memory_summary = self.memory_manager.get_conversation_summary()
        context_summary = self.context_manager.get_context_summary()
        
        return {
            **memory_summary,
            "question_context": context_summary
        }
    
