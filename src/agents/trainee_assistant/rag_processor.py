from typing import List, Dict, Any
from src.agents.trainee_assistant.models import MessageType, SearchResult
from src.agents.trainee_assistant.tools import VectorSearchTool, WebSearchTool
from src.agents.trainee_assistant.memory_manager import ConversationMemoryManager
from config.settings import settings 
import openai  # 실제 LLM 사용 시 필요

# OpenAI 설정
openai.api_key = settings.api_key

class RAGProcessor:
    """RAG(Retrieval-Augmented Generation) 처리 클래스"""
    
    def __init__(self, document_name: str, similarity_threshold: float = 0.7):
        self.similarity_threshold = similarity_threshold
        self.vector_search_tool = VectorSearchTool(document_name=document_name)
        self.web_search_tool = WebSearchTool(
            api_key=settings.google_api_key,
            cx=settings.google_cx_id
        )
        self.last_workflow_info = {}
    
    async def info_node(self, query: str, memory_manager: ConversationMemoryManager) -> Dict[str, Any]:
        """
        🔵 [2] info 노드 실행
        질문 내용을 기반으로 ChromaDB에 유사도 검색하고 다음 단계 결정
        """
        # 도구 호출 로그 추가
        memory_manager.add_message(
            MessageType.TOOL_CALL, 
            f"관련 학습 자료 검색 실행: {query}",
            {"tool": "vector_search", "query": query}
        )
        
        # 벡터 검색 실행
        vector_results = await self.vector_search_tool.search(query, n_results=5)
        
        # 검색 결과 로그 추가
        memory_manager.add_message(
            MessageType.TOOL_RESULT,
            f"학습 자료 검색 결과: {len(vector_results)}개 자료 발견",
            {"tool": "vector_search", "results_count": len(vector_results)}
        )
        
        # 유사도 임계값 이상의 결과가 있는지 확인
        high_similarity_results = [
            result for result in vector_results 
            if result.score >= self.similarity_threshold
        ]
        
        # 워크플로우 정보 업데이트
        if high_similarity_results:
            # ✅ 검색 결과 있음 → vector_search_tool 호출 준비
            workflow_info = {
                "search_executed": True,
                "search_query": query,
                "search_result": {
                    "source": "vector_search",
                    "results_count": len(high_similarity_results),
                    "avg_similarity": sum(r.score for r in high_similarity_results) / len(high_similarity_results),
                    "threshold_met": True
                },
                "next_action": "use_vector_search"
            }
            
            self.last_workflow_info = workflow_info
            
            return {
                "next_action": "use_vector_search",
                "results": high_similarity_results,
                "message": f"관련 학습 자료 {len(high_similarity_results)}개를 찾았습니다.",
                "workflow_info": workflow_info
            }
        else:
            # ❌ 검색 결과 없음 → web_search_tool 호출 준비
            workflow_info = {
                "search_executed": True,
                "search_query": query,
                "search_result": {
                    "source": "vector_search",
                    "results_count": len(vector_results),
                    "threshold_met": False,
                    "will_fallback_to_web": True
                },
                "next_action": "use_web_search",
            }
            
            self.last_workflow_info = workflow_info
            
            return {
                "next_action": "use_web_search",
                "results": [],
                "message": "관련 학습 자료를 찾지 못했습니다. 온라인 자료 검색을 시도합니다.",
                "workflow_info": workflow_info
            }
    
    async def vector_search_node(self, query: str, results: List[SearchResult], system_prompt: str) -> str:
        """
        🟡 [3A] vector_search 노드 실행
        ChromaDB 검색 결과를 기반으로 응답 생성
        """
        # 워크플로우 정보 업데이트
        self.last_workflow_info.update({
            "final_action": "vector_search_response_generated",
            "documents_used": len(results[:3])
        })
        
        # 검색 결과를 컨텍스트로 사용
        context_content = "\n\n".join([
            f"[학습 자료 {i+1}] (관련도: {result.score:.2f})\n{result.content}"
            for i, result in enumerate(results[:3])  # 상위 3개 결과만 사용
        ])
        
        enhanced_prompt = f"""{system_prompt}

관련 학습 자료:
{context_content}

위 학습 자료를 참고하여 학습자의 질문에 답변해주세요. 자료의 내용을 바탕으로 정확하고 이해하기 쉽게 설명해주세요."""
        
        # LLM API 호출하여 응답 생성
        response = await self._generate_response_with_context(query, enhanced_prompt)
        
        return response
    
    async def web_search_node(self, query: str, system_prompt: str, memory_manager: ConversationMemoryManager) -> str:
        """
        🟡 [3B] web_search 노드 실행
        웹 검색 결과를 기반으로 응답 생성
        """
        # 웹 검색 실행
        memory_manager.add_message(
            MessageType.TOOL_CALL,
            f"온라인 학습 자료 검색 실행: {query}",
            {"tool": "web_search", "query": query}
        )
        
        web_results = await self.web_search_tool.search(query, num_results=3)
        
        memory_manager.add_message(
            MessageType.TOOL_RESULT,
            f"온라인 검색 결과: {len(web_results)}개 자료 발견",
            {"tool": "web_search", "results_count": len(web_results)}
        )
        
        # 워크플로우 정보 업데이트
        self.last_workflow_info.update({
            "web_search_executed": True,
            "web_results_count": len(web_results),
            "final_action": "web_search_response_generated"
        })
        
        if not web_results:
            self.last_workflow_info.update({"final_action": "no_results_found"})
            return """죄송합니다. 관련 학습 자료를 찾지 못했습니다. 
하지만 문제와 정답 정보를 바탕으로 최대한 도움을 드리겠습니다. 
구체적으로 어떤 부분이 궁금하신지 더 자세히 알려주시면 더 나은 설명을 제공할 수 있습니다."""
        
        # 웹 검색 결과를 컨텍스트로 사용
        context_content = "\n\n".join([
            f"[온라인 자료 {i+1}]\n{result.content}"
            for i, result in enumerate(web_results)
        ])
        
        enhanced_prompt = f"""{system_prompt}

온라인 학습 자료:
{context_content}

위 온라인 자료를 참고하여 학습자의 질문에 답변해주세요. 자료의 출처를 명시하고, 신뢰할 수 있는 정보를 제공해주세요."""
        
        response = await self._generate_response_with_context(query, enhanced_prompt)
        
        return response
    
    def get_workflow_info(self) -> Dict[str, Any]:
        """현재 워크플로우 정보 반환"""
        return self.last_workflow_info.copy()
    
    async def _generate_response_with_context(self, user_message: str, system_prompt: str) -> str:
        """컨텍스트가 포함된 응답 생성"""
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]

            response = await openai.ChatCompletion.acreate(
                model="gpt-4o",
                messages=messages,
                temperature=0.7
            )

            return response.choices[0].message.content
        
        except Exception as e:
            print(f"LLM 호출 오류: {e}")
            return "죄송합니다. 현재 응답을 생성하는 데 문제가 발생했습니다. 다시 시도해 주세요."
        
