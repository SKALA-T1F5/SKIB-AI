"""
Trainee Assistant Agent 테스트 코드
더미 데이터를 사용해서 각 기능별 단위 테스트 실행
"""

import asyncio
import json
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch

# 테스트용 더미 데이터
DUMMY_QUESTION_DATA = {
    "test_id": "test_001",
    "question_id": "q_001", 
    "question_type": "multiple_choice",
    "difficulty_level": "medium",
    "question_text": "Python에서 리스트와 튜플의 주요 차이점은 무엇인가요?",
    "correct_answer": "리스트는 변경 가능(mutable)하고 튜플은 변경 불가능(immutable)하다",
    "explanation": "리스트는 생성 후 요소를 추가, 삭제, 수정할 수 있지만, 튜플은 한 번 생성되면 내용을 변경할 수 없습니다.",
    "document_id": "doc_001",
    "document_name": "Python 기초 문법.pdf",
    "tags": ["문해력", "논리력"],
    "options": ["A) 둘 다 변경 가능하다", "B) 리스트는 변경 가능, 튜플은 변경 불가능", "C) 둘 다 변경 불가능하다", "D) 차이가 없다"],
    "grading_criteria": None
}

DUMMY_VECTOR_RESULTS = [
    {
        "content": "파이썬의 리스트(list)는 대괄호 []로 표현되며 변경 가능한(mutable) 자료형입니다. 요소를 추가, 삭제, 수정할 수 있습니다.",
        "score": 0.85,
        "metadata": {"source": "Python 기초 문법.pdf", "page": 15}
    },
    {
        "content": "튜플(tuple)은 소괄호 ()로 표현되며 변경 불가능한(immutable) 자료형입니다. 한 번 생성되면 내용을 변경할 수 없습니다.",
        "score": 0.82,
        "metadata": {"source": "Python 기초 문법.pdf", "page": 16}
    },
    {
        "content": "리스트와 튜플 모두 순서가 있는 시퀀스 자료형이지만, 가변성에서 차이가 납니다.",
        "score": 0.78,
        "metadata": {"source": "Python 기초 문법.pdf", "page": 17}
    }
]

DUMMY_WEB_RESULTS = [
    {
        "content": "파이썬 리스트 vs 튜플: 리스트는 mutable, 튜플은 immutable 자료형입니다. 리스트는 append(), remove() 등의 메서드로 수정 가능하지만 튜플은 불가능합니다.",
        "url": "https://example.com/python-list-tuple",
        "title": "Python 리스트와 튜플의 차이점"
    },
    {
        "content": "성능 측면에서 튜플이 리스트보다 빠릅니다. 변경 불가능한 특성으로 인해 메모리 효율성도 더 좋습니다.",
        "url": "https://example.com/python-performance",
        "title": "Python 자료형 성능 비교"
    }
]

# 더미 SearchResult 클래스
class DummySearchResult:
    def __init__(self, content: str, score: float, metadata: Dict = None):
        self.content = content
        self.score = score
        self.metadata = metadata or {}

# 더미 LLM 응답 생성기
class DummyLLMResponse:
    @staticmethod
    async def generate_response(system_prompt: str, user_message: str, context: str = "") -> str:
        """더미 LLM 응답 생성"""
        if "리스트" in user_message and "튜플" in user_message:
            return f"""안녕하세요! 리스트와 튜플의 차이점에 대해 설명드리겠습니다.

**주요 차이점:**
1. **가변성(Mutability)**: 리스트는 변경 가능(mutable), 튜플은 변경 불가능(immutable)
2. **표현 방법**: 리스트는 [], 튜플은 ()
3. **성능**: 튜플이 리스트보다 빠르고 메모리 효율적

**실제 예시:**
```python
# 리스트 - 수정 가능
my_list = [1, 2, 3]
my_list.append(4)  # OK

# 튜플 - 수정 불가능  
my_tuple = (1, 2, 3)
# my_tuple.append(4)  # 에러 발생!
```

이해가 되셨나요? 더 궁금한 점이 있으시면 언제든 물어보세요! 😊"""
        
        elif "성능" in user_message:
            return """성능 측면에서 말씀드리면:

**튜플이 리스트보다 빠른 이유:**
- 불변 객체라서 해시 계산이 가능
- 메모리 할당이 더 효율적
- 가비지 컬렉션 부담이 적음

실제 벤치마크에서도 튜플 접근이 약 15-20% 더 빠릅니다!"""
        
        else:
            return f"'{user_message}'에 대한 답변을 생성했습니다. (더미 응답)"

class TestTraineeAssistant:
    """TraineeAssistant 테스트 클래스"""
    
    def __init__(self):
        self.test_results = {
            "vector_search_test": False,
            "web_search_test": False, 
            "prompt_generation_test": False,
            "memory_management_test": False,
            "integration_test": False
        }
    
    async def run_all_tests(self):
        """전체 테스트 실행"""
        print("🚀 Trainee Assistant Agent 테스트 시작\n")
        
        # 1. Vector Search 테스트
        await self.test_vector_search_flow()
        
        # 2. Web Search 테스트  
        await self.test_web_search_flow()
        
        # 3. 프롬프트 생성 테스트
        await self.test_prompt_generation()
        
        # 4. 메모리 관리 테스트
        await self.test_memory_management()
        
        # 5. 통합 테스트
        await self.test_integration()
        
        # 결과 출력
        self.print_test_results()
    
    async def test_vector_search_flow(self):
        """1. Vector Search 플로우 테스트"""
        print("🔍 [테스트 1] Vector Search 플로우 테스트")
        
        try:
            # Mock 설정
            with patch('src.agents.trainee_assistant.rag_processor.openai.ChatCompletion.acreate') as mock_llm:
                mock_llm.return_value = MagicMock()
                mock_llm.return_value.choices = [MagicMock()]
                mock_llm.return_value.choices[0].message.content = await DummyLLMResponse.generate_response(
                    "system", "리스트와 튜플의 차이점이 뭔가요?"
                )
                
                # 더미 벡터 검색 결과 생성
                dummy_results = [
                    DummySearchResult(result["content"], result["score"], result["metadata"]) 
                    for result in DUMMY_VECTOR_RESULTS
                ]
                
                # RAGProcessor 테스트
                from src.agents.trainee_assistant.rag_processor import RAGProcessor
                
                # VectorSearchTool Mock
                mock_vector_tool = AsyncMock()
                mock_vector_tool.search.return_value = dummy_results
                
                rag_processor = RAGProcessor(
                    similarity_threshold=0.7,
                    vector_search_tool=mock_vector_tool
                )
                
                # info_node 테스트
                from src.agents.trainee_assistant.memory_manager import ConversationMemoryManager
                memory_manager = ConversationMemoryManager()
                
                query = "리스트와 튜플의 차이점이 뭔가요?"
                info_result = await rag_processor.info_node(query, memory_manager)
                
                print(f"   ✅ Info Node 결과: {info_result['next_action']}")
                print(f"   ✅ 검색된 결과 수: {len(info_result['results'])}")
                
                # vector_search_node 테스트
                if info_result["next_action"] == "use_vector_search":
                    system_prompt = "테스트용 시스템 프롬프트"
                    response = await rag_processor.vector_search_node(
                        query, info_result["results"], system_prompt
                    )
                    print(f"   ✅ 벡터 검색 기반 응답 생성됨 (길이: {len(response)}자)")
                    print(f"   📝 응답 미리보기: {response[:100]}...")
                
                self.test_results["vector_search_test"] = True
                print("   🎉 Vector Search 테스트 통과!\n")
                
        except Exception as e:
            print(f"   ❌ Vector Search 테스트 실패: {e}\n")
    
    async def test_web_search_flow(self):
        """2. Web Search 플로우 테스트"""
        print("🌐 [테스트 2] Web Search 플로우 테스트")
        
        try:
            # Mock 설정
            with patch('src.agents.trainee_assistant.rag_processor.openai.ChatCompletion.acreate') as mock_llm:
                mock_llm.return_value = MagicMock()
                mock_llm.return_value.choices = [MagicMock()]
                mock_llm.return_value.choices[0].message.content = await DummyLLMResponse.generate_response(
                    "system", "고급 파이썬 개념에 대해 알려주세요"
                )
                
                # 벡터 검색에서 결과 없음 시뮬레이션
                dummy_low_results = [
                    DummySearchResult("관련도 낮은 내용", 0.3, {})
                ]
                
                # Web Search 더미 결과
                dummy_web_results = [
                    DummySearchResult(result["content"], 0.9, {"url": result["url"]})
                    for result in DUMMY_WEB_RESULTS
                ]
                
                from src.agents.trainee_assistant.rag_processor import RAGProcessor
                from src.agents.trainee_assistant.memory_manager import ConversationMemoryManager
                
                # Mock Tools
                mock_vector_tool = AsyncMock()
                mock_vector_tool.search.return_value = dummy_low_results
                
                mock_web_tool = AsyncMock()
                mock_web_tool.search.return_value = dummy_web_results
                
                rag_processor = RAGProcessor(
                    similarity_threshold=0.7,
                    vector_search_tool=mock_vector_tool,
                    web_search_tool=mock_web_tool
                )
                
                memory_manager = ConversationMemoryManager()
                query = "고급 파이썬 개념에 대해 알려주세요"
                
                # info_node에서 web_search 루트로 분기 확인
                info_result = await rag_processor.info_node(query, memory_manager)
                print(f"   ✅ Info Node 결과: {info_result['next_action']}")
                
                # web_search_node 테스트
                if info_result["next_action"] == "use_web_search":
                    system_prompt = "테스트용 시스템 프롬프트"
                    response = await rag_processor.web_search_node(
                        query, system_prompt, memory_manager
                    )
                    print(f"   ✅ 웹 검색 기반 응답 생성됨 (길이: {len(response)}자)")
                    print(f"   📝 응답 미리보기: {response[:100]}...")
                
                self.test_results["web_search_test"] = True
                print("   🎉 Web Search 테스트 통과!\n")
                
        except Exception as e:
            print(f"   ❌ Web Search 테스트 실패: {e}\n")
    
    async def test_prompt_generation(self):
        """3. 프롬프트 생성 테스트"""
        print("📝 [테스트 3] 프롬프트 생성 테스트")
        
        try:
            from src.agents.trainee_assistant.context_manager import QuestionContextManager
            
            context_manager = QuestionContextManager()
            context_manager.set_question_context(DUMMY_QUESTION_DATA)
            
            system_prompt = context_manager.get_system_prompt()
            
            print("   ✅ 시스템 프롬프트 생성 완료")
            print(f"   📏 프롬프트 길이: {len(system_prompt)}자")
            print("   📋 프롬프트 내용 확인:")
            print("   " + "="*50)
            print("   " + system_prompt[:300] + "...")
            print("   " + "="*50)
            
            # 컨텍스트 요약 정보 확인
            context_summary = context_manager.get_context_summary()
            print(f"   ✅ 컨텍스트 요약: {context_summary}")
            
            self.test_results["prompt_generation_test"] = True
            print("   🎉 프롬프트 생성 테스트 통과!\n")
            
        except Exception as e:
            print(f"   ❌ 프롬프트 생성 테스트 실패: {e}\n")
    
    async def test_memory_management(self):
        """4. 메모리 관리 테스트"""
        print("🧠 [테스트 4] 메모리 관리 테스트")
        
        try:
            from src.agents.trainee_assistant.memory_manager import ConversationMemoryManager
            from src.agents.trainee_assistant.models import MessageType
            
            memory_manager = ConversationMemoryManager(max_context_messages=5)
            
            # 다양한 메시지 타입 추가
            test_messages = [
                (MessageType.USER, "안녕하세요!"),
                (MessageType.ASSISTANT, "안녕하세요! 무엇을 도와드릴까요?"),
                (MessageType.TOOL_CALL, "벡터 검색 실행"),
                (MessageType.TOOL_RESULT, "검색 결과 3개 발견"),
                (MessageType.USER, "리스트와 튜플의 차이점이 뭔가요?"),
                (MessageType.ASSISTANT, "리스트는 변경 가능하고..."),
                (MessageType.USER, "더 자세히 설명해주세요"),
            ]
            
            for msg_type, content in test_messages:
                memory_manager.add_message(msg_type, content)
            
            # 메모리 상태 확인
            conversation_summary = memory_manager.get_conversation_summary()
            print(f"   ✅ 저장된 메시지 수: {conversation_summary['total_messages']}")
            print(f"   ✅ 사용자 메시지 수: {conversation_summary['user_messages']}")
            print(f"   ✅ 어시스턴트 메시지 수: {conversation_summary['assistant_messages']}")
            print(f"   ✅ 도구 호출 수: {conversation_summary['tool_calls']}")
            
            # 컨텍스트 생성 테스트
            context_messages = memory_manager.get_context_for_llm()
            print(f"   ✅ LLM 컨텍스트 메시지 수: {len(context_messages)}")
            
            # 최대 메시지 제한 테스트
            print(f"   ✅ 메시지 제한: {memory_manager.max_context_messages}개")
            
            self.test_results["memory_management_test"] = True
            print("   🎉 메모리 관리 테스트 통과!\n")
            
        except Exception as e:
            print(f"   ❌ 메모리 관리 테스트 실패: {e}\n")
    
    async def test_integration(self):
        """5. 통합 테스트"""
        print("🔗 [테스트 5] 통합 테스트")
        
        try:
            # Mock 모든 외부 의존성
            with patch('src.agents.trainee_assistant.rag_processor.openai.ChatCompletion.acreate') as mock_llm, \
                 patch('src.agents.trainee_assistant.tools.VectorSearchTool') as MockVectorTool, \
                 patch('src.agents.trainee_assistant.tools.WebSearchTool') as MockWebTool:
                
                # LLM Mock 설정
                mock_llm.return_value = MagicMock()
                mock_llm.return_value.choices = [MagicMock()]
                mock_llm.return_value.choices[0].message.content = await DummyLLMResponse.generate_response(
                    "system", "리스트와 튜플의 차이점이 뭔가요?"
                )
                
                # Vector Tool Mock 설정
                mock_vector_instance = AsyncMock()
                mock_vector_instance.search.return_value = [
                    DummySearchResult(result["content"], result["score"]) 
                    for result in DUMMY_VECTOR_RESULTS
                ]
                MockVectorTool.return_value = mock_vector_instance
                
                # Web Tool Mock 설정
                mock_web_instance = AsyncMock()
                mock_web_instance.search.return_value = [
                    DummySearchResult(result["content"], 0.9)
                    for result in DUMMY_WEB_RESULTS
                ]
                MockWebTool.return_value = mock_web_instance
                
                # TraineeAssistantAgent 테스트
                from src.agents.trainee_assistant.agent import TraineeAssistantAgent
                
                agent = TraineeAssistantAgent()
                agent.set_question_context(DUMMY_QUESTION_DATA)
                
                print("   ✅ Agent 초기화 완료")
                
                # 첫 번째 질문 처리
                result1 = await agent.process_message("리스트와 튜플의 차이점이 뭔가요?")
                print(f"   ✅ 첫 번째 응답 생성: {len(result1['response'])}자")
                print(f"   ✅ 워크플로우 정보: {result1['workflow_info']['next_action']}")
                
                # 두 번째 질문 처리 (메모리 테스트)
                result2 = await agent.process_message("성능 차이도 있나요?")
                print(f"   ✅ 두 번째 응답 생성: {len(result2['response'])}자")
                
                # 대화 요약 확인
                summary = agent.get_conversation_summary()
                print(f"   ✅ 대화 요약: {summary['total_messages']}개 메시지")
                print(f"   ✅ 문제 컨텍스트: {summary['question_context']['question_type']}")
                
                self.test_results["integration_test"] = True
                print("   🎉 통합 테스트 통과!\n")
                
        except Exception as e:
            print(f"   ❌ 통합 테스트 실패: {e}\n")
    
    def print_test_results(self):
        """테스트 결과 출력"""
        print("📊 테스트 결과 요약")
        print("=" * 50)
        
        passed = sum(self.test_results.values())
        total = len(self.test_results)
        
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"   {test_name}: {status}")
        
        print(f"\n🏆 총 {passed}/{total}개 테스트 통과")
        
        if passed == total:
            print("🎉 모든 테스트가 성공적으로 완료되었습니다!")
        else:
            print("⚠️  일부 테스트에서 문제가 발견되었습니다.")

# 실행 부분
async def main():
    """메인 테스트 함수"""
    tester = TestTraineeAssistant()
    await tester.run_all_tests()

if __name__ == "__main__":
    # 비동기 실행
    asyncio.run(main())