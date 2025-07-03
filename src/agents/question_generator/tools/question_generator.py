"""
질문 생성 도구
- GPT-4 Vision을 사용한 자동 질문 생성
- 블록을 Vision API용 청크로 변환
- 객관식/주관식 문제 생성
"""

import base64
import json
import os
from typing import Dict, List

import google.generativeai as genai
from dotenv import load_dotenv
from langsmith import traceable

from .prompt import get_vision_prompt, get_enhanced_vision_prompt
from src.utils.gemini_monitoring import GeminiMonitor

# 환경 변수 로드
load_dotenv(override=True)
gemini_api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=gemini_api_key)

# Gemini 모니터링 인스턴스
gemini_monitor = GeminiMonitor()


@traceable(
    run_type="chain",
    name="Gemini Question Generator",
    metadata={"agent_type": "question_generator"}
)
def _generate_gemini_questions(
    messages: List[Dict],
    system_prompt: str,
    num_objective: int = 1,
    num_subjective: int = 1,
) -> List[Dict]:
    """
    공통 Gemini 질문 생성 함수 (중복 제거)
    
    Args:
        messages: Vision API 메시지 배열
        system_prompt: 시스템 프롬프트
        num_objective: 객관식 문제 수
        num_subjective: 주관식 문제 수
    
    Returns:
        List[Dict]: 생성된 질문 목록
    """
    try:
        print(f"  🤖 Gemini 2.5 Pro 호출 중... (객관식: {num_objective}, 주관식: {num_subjective})")

        # Gemini 2.5 Pro 모델 초기화 (안전 설정 완전 해제)
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]

        model = genai.GenerativeModel("gemini-2.0-flash-exp", safety_settings=safety_settings)

        # Gemini용 메시지 구성
        gemini_parts = [system_prompt]

        for message in messages:
            if message.get("type") == "text":
                gemini_parts.append(message["text"])
            elif message.get("type") == "image_url":
                import io
                from PIL import Image

                image_url = message["image_url"]["url"]
                if image_url.startswith("data:image"):
                    base64_data = image_url.split(",")[1]
                    image_data = base64.b64decode(base64_data)
                    image = Image.open(io.BytesIO(image_data))
                    gemini_parts.append(image)

        # Gemini API 호출 (안전 필터 우회를 위한 설정)
        response = model.generate_content(
            gemini_parts,
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,  # 낮은 온도로 안정적인 응답 유도
                max_output_tokens=3000,  # 더 많은 토큰 허용
                top_p=0.8,  # 다양성 조절
                top_k=40,   # 상위 토큰 제한
                candidate_count=1,  # 하나의 후보만 생성
                stop_sequences=[]  # 중단 시퀀스 없음
            ),
        )

        # 첫 번째 API 호출 모니터링
        model_name = "gemini-2.0-flash-exp"
        if hasattr(response, 'usage_metadata'):
            gemini_monitor.print_usage_summary(model_name, response.usage_metadata)
            gemini_monitor.log_usage(
                model_name, 
                response.usage_metadata, 
                function_name="question_generator_gemini",
                additional_metadata={
                    "agent_type": "question_generator",
                    "num_objective": num_objective,
                    "num_subjective": num_subjective,
                    "attempt": "primary"
                }
            )

        # 안전한 응답 처리 및 재시도 로직
        max_retries = 2
        retry_count = 0
        
        while retry_count < max_retries:
            if response.candidates and response.candidates[0].content.parts:
                raw_content = response.text.strip()
                print(f"  📄 응답 내용 미리보기: {raw_content[:100]}...")
                break
            else:
                finish_reason = response.candidates[0].finish_reason if response.candidates else 'N/A'
                print(f"  ⚠️ Gemini 응답이 차단됨 (finish_reason: {finish_reason})")
                
                # finish_reason이 2(SAFETY)인 경우 재시도
                if finish_reason == 2 and retry_count < max_retries - 1:
                    retry_count += 1
                    print(f"  🔄 재시도 {retry_count}/{max_retries}...")
                    
                    # 더 보수적인 설정으로 재시도
                    response = model.generate_content(
                        gemini_parts,
                        generation_config=genai.types.GenerationConfig(
                            temperature=0.1,  # 더 낮은 온도
                            max_output_tokens=2000,
                            top_p=0.6,
                            top_k=20,
                            candidate_count=1
                        ),
                    )
                    
                    # 재시도 API 호출 모니터링
                    if hasattr(response, 'usage_metadata'):
                        gemini_monitor.print_usage_summary(model_name, response.usage_metadata)
                        gemini_monitor.log_usage(
                            model_name, 
                            response.usage_metadata, 
                            function_name="question_generator_gemini_retry",
                            additional_metadata={
                                "agent_type": "question_generator",
                                "num_objective": num_objective,
                                "num_subjective": num_subjective,
                                "attempt": f"retry_{retry_count}"
                            }
                        )
                else:
                    print(f"  ❌ 최대 재시도 횟수 초과 또는 다른 에러")
                    return []

        # JSON 파싱
        try:
            # 코드 블록 제거
            if "```json" in raw_content:
                raw_content = raw_content.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_content:
                raw_content = raw_content.split("```")[1].split("```")[0].strip()

            # JSON이 잘린 경우 복구 시도
            if not raw_content.strip().endswith("]"):
                # 배열이 완료되지 않은 경우, 마지막 객체 제거
                if raw_content.strip().endswith(","):
                    raw_content = raw_content.strip()[:-1]

                # 불완전한 마지막 객체 제거
                bracket_count = 0
                valid_end = -1
                for i, char in enumerate(raw_content):
                    if char == "{":
                        bracket_count += 1
                    elif char == "}":
                        bracket_count -= 1
                        if bracket_count == 0:
                            valid_end = i

                if valid_end > 0:
                    raw_content = raw_content[: valid_end + 1] + "]"
                else:
                    raw_content += "]"

            questions = json.loads(raw_content)

            # 리스트인지 확인
            if not isinstance(questions, list):
                print(f"⚠️ 응답이 리스트가 아닙니다: {type(questions)}")
                return []

            print(f"  ✅ {len(questions)}개 질문 파싱 성공")
            return questions

        except json.JSONDecodeError as e:
            print(f"  ❌ JSON 파싱 실패: {e}")
            print(f"  원본 응답 길이: {len(raw_content)} 문자")
            print(f"  응답 마지막 100자: ...{raw_content[-100:]}")
            return []

    except Exception as e:
        print(f"  ❌ 질문 생성 실패: {e}")
        import traceback
        print(f"  📄 상세 오류: {traceback.format_exc()}")
        return []


def generate_question_with_test_plan(
    messages: List[Dict],
    source: str,
    page: str,
    num_objective: int = 1,
    num_subjective: int = 1,
    difficulty: str = "NORMAL",
    total_test_plan: Dict = None,
    document_test_plan: Dict = None,
) -> List[Dict]:
    """
    Test Plan 정보를 활용하여 Gemini 2.5 Pro로 질문을 생성하는 함수

    Args:
        messages: Vision API 메시지 배열 (텍스트 및 이미지 포함)
        source: 문서 소스 파일명
        page: 페이지 번호
        num_objective: 객관식 문제 수
        num_subjective: 주관식 문제 수
        difficulty: 난이도 (EASY, NORMAL, HARD)
        total_test_plan: 전체 테스트 계획 정보
        document_test_plan: 문서별 테스트 계획 정보

    Returns:
        List[Dict]: 생성된 질문 목록
    """
    # Test Plan 정보를 활용한 프롬프트 생성
    system_prompt = get_enhanced_vision_prompt(
        source, page, difficulty, num_objective, num_subjective,
        total_test_plan, document_test_plan
    )
    
    return _generate_gemini_questions(messages, system_prompt, num_objective, num_subjective)


def generate_question(
    messages: List[Dict],
    source: str,
    page: str,
    num_objective: int = 1,
    num_subjective: int = 1,
    difficulty: str = "NORMAL",
) -> List[Dict]:
    """
    Gemini 2.5 Pro를 사용하여 질문을 생성하는 함수

    Args:
        messages: Vision API 메시지 배열 (텍스트 및 이미지 포함)
        source: 문서 소스 파일명
        page: 페이지 번호
        num_objective: 객관식 문제 수
        num_subjective: 주관식 문제 수
        difficulty: 난이도 (EASY, NORMAL, HARD)

    Returns:
        List[Dict]: 생성된 질문 목록
    """
    # Vision API용 프롬프트 생성
    system_prompt = get_vision_prompt(
        source, page, difficulty, num_objective, num_subjective
    )
    
    return _generate_gemini_questions(messages, system_prompt, num_objective, num_subjective)


# 기존 Gemini 버전 (주석 처리)
"""
def generate_question_gemini(
    messages: List[Dict], 
    source: str, 
    page: str, 
    num_objective: int = 1, 
    num_subjective: int = 1,
    difficulty: str = "NORMAL"
) -> List[Dict]:
    try:
        system_prompt = get_vision_prompt(source, page, difficulty, num_objective, num_subjective)

        print(f"  🤖 Gemini 2.5 Flash 호출 중... (객관식: {num_objective}, 주관식: {num_subjective})")

        model = genai.GenerativeModel('gemini-2.0-flash-exp')

        gemini_parts = []
        gemini_parts.append(system_prompt)

        for message in messages:
            if message.get("type") == "text":
                gemini_parts.append(message["text"])
            elif message.get("type") == "image_url":
                import io
                from PIL import Image

                image_url = message["image_url"]["url"]
                if image_url.startswith("data:image"):
                    base64_data = image_url.split(",")[1]
                    image_data = base64.b64decode(base64_data)
                    image = Image.open(io.BytesIO(image_data))
                    gemini_parts.append(image)

        response = model.generate_content(
            gemini_parts,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=2000,
            )
        )

        raw_content = response.text.strip()

        if "```json" in raw_content:
            raw_content = raw_content.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_content:
            raw_content = raw_content.split("```")[1].split("```")[0].strip()

        questions = json.loads(raw_content)

        if not isinstance(questions, list):
            return []

        return questions
    except Exception as e:
        print(f"  ❌ 질문 생성 실패: {e}")
        return []
"""


class QuestionGenerator:
    """질문 생성 클래스"""

    def __init__(self, image_save_dir: str = "data/images"):
        """
        QuestionGenerator 초기화

        Args:
            image_save_dir: 이미지 파일이 저장된 디렉토리 경로
        """
        self.image_save_dir = image_save_dir

    def generate_questions_with_test_plans(
        self, 
        blocks: List[Dict], 
        num_objective: int = 3, 
        num_subjective: int = 3,
        total_test_plan_path: str = None,
        document_test_plan_path: str = None,
        source_document_name: str = None
    ) -> List[Dict]:
        """
        Test Plan 정보를 활용하여 블록들에 대해 질문 생성

        Args:
            blocks: 문서 블록들
            num_objective: 객관식 문제 수 (기본값, document_test_plan의 추천값으로 대체 가능)
            num_subjective: 주관식 문제 수 (기본값, document_test_plan의 추천값으로 대체 가능)
            total_test_plan_path: 전체 테스트 계획 JSON 파일 경로
            document_test_plan_path: 문서별 테스트 계획 JSON 파일 경로
            source_document_name: 소스 문서명 (document_test_plan에서 찾기 위함)

        Returns:
            List[Dict]: 질문이 추가된 블록들
        """
        print("🤖 Test Plan 기반 Gemini 2.5 Pro 질문 생성 중...")

        # Test Plan 파일 로드
        total_test_plan = self._load_test_plan(total_test_plan_path) if total_test_plan_path else None
        document_test_plan_data = self._load_test_plan(document_test_plan_path) if document_test_plan_path else None

        # 현재 문서에 해당하는 document_test_plan 찾기
        document_test_plan = self._find_document_plan(document_test_plan_data, source_document_name)

        if total_test_plan:
            test_name = total_test_plan.get('test_plan', {}).get('name', '알 수 없음')
            print(f"📋 전체 테스트 계획 로드: {test_name}")
        
        if document_test_plan:
            doc_name = document_test_plan.get('document_name', '알 수 없음')
            print(f"📄 문서별 계획 로드: {doc_name}")
            
            # document_test_plan의 추천 문제 수 사용
            recommended = document_test_plan.get('recommended_questions', {})
            if recommended:
                num_objective = recommended.get('objective', num_objective)
                num_subjective = recommended.get('subjective', num_subjective)
                print(f"📊 추천 문제 수 적용 - 객관식: {num_objective}, 주관식: {num_subjective}")

        try:
            # 블록들을 청킹하여 Gemini 2.5 Pro 메시지 생성
            vision_chunks = self._blocks_to_vision_chunks(blocks)
            total_questions_target = num_objective + num_subjective
            
            print(f"📝 목표 문제 수: {total_questions_target}개 (객관식: {num_objective}, 주관식: {num_subjective})")

            # 1단계: 기본 문제 생성
            questions_generated = self._generate_basic_questions(
                vision_chunks, blocks, num_objective, num_subjective, 
                total_test_plan, document_test_plan
            )

            # 2단계: 여분 문제 생성 (각 타입별로 2문제씩 추가)
            if document_test_plan and document_test_plan.get('keywords'):
                extra_questions = self._generate_extra_questions(
                    vision_chunks[0] if vision_chunks else None,  # 첫 번째 청크 사용
                    document_test_plan,
                    total_test_plan,
                    extra_objective=2,
                    extra_subjective=2
                )
                
                if extra_questions and vision_chunks:
                    # 첫 번째 블록에 여분 문제 추가
                    chunk = vision_chunks[0]
                    if chunk["block_indices"]:
                        first_block_idx = chunk["block_indices"][0]
                        if "questions" not in blocks[first_block_idx]:
                            blocks[first_block_idx]["questions"] = []
                        blocks[first_block_idx]["questions"].extend(extra_questions)
                        print(f"    ➕ {len(extra_questions)}개 여분 문제 추가")

            total_generated = sum(len(b.get("questions", [])) for b in blocks)
            print(f"✅ 총 {total_generated}개 질문 생성 완료")

        except Exception as e:
            print(f"❌ 질문 생성 중 오류: {e}")

        return blocks

    def _find_document_plan(self, document_test_plan_data: Dict, source_document_name: str) -> Dict:
        """document_test_plan에서 현재 문서에 해당하는 계획 찾기"""
        if not document_test_plan_data or not source_document_name:
            return {}
        
        document_plans = document_test_plan_data.get('document_plans', [])
        for plan in document_plans:
            if source_document_name in plan.get('document_name', ''):
                return plan
        
        return {}

    def _generate_basic_questions(
        self, vision_chunks, blocks, num_objective, num_subjective, 
        total_test_plan, document_test_plan
    ) -> int:
        """기본 문제 생성"""
        questions_generated = 0
        
        for i, chunk in enumerate(vision_chunks):
            print(f"  📝 청크 {i+1}/{len(vision_chunks)} 기본 문제 생성 중...")

            # 청크별 문제 수 분배 (단순하게)
            chunk_obj = num_objective // len(vision_chunks)
            chunk_subj = num_subjective // len(vision_chunks)
            
            # 마지막 청크에서 나머지 처리
            if i == len(vision_chunks) - 1:
                chunk_obj += num_objective % len(vision_chunks)
                chunk_subj += num_subjective % len(vision_chunks)

            if chunk_obj == 0 and chunk_subj == 0:
                continue

            try:
                # Test Plan 정보를 활용한 질문 생성
                questions = generate_question_with_test_plan(
                    messages=chunk["messages"],
                    source=chunk["metadata"].get("source", "unknown"),
                    page=str(chunk["metadata"].get("page", "N/A")),
                    num_objective=chunk_obj,
                    num_subjective=chunk_subj,
                    total_test_plan=total_test_plan,
                    document_test_plan=document_test_plan,
                )

                # 첫 번째 블록에 질문 추가 (청크 대표)
                if chunk["block_indices"] and questions:
                    first_block_idx = chunk["block_indices"][0]
                    if "questions" not in blocks[first_block_idx]:
                        blocks[first_block_idx]["questions"] = []
                    blocks[first_block_idx]["questions"].extend(questions)
                    questions_generated += len(questions)

                    print(f"    ✅ {len(questions)}개 기본 문제 생성")

            except Exception as e:
                print(f"    ⚠️ 청크 {i+1} 기본 문제 생성 실패: {e}")
                continue
        
        return questions_generated

    def _generate_extra_questions(
        self, chunk, document_test_plan, total_test_plan, 
        extra_objective=2, extra_subjective=2
    ) -> List[Dict]:
        """여분 문제 생성 (키워드 기반)"""
        if not chunk or not document_test_plan:
            return []
        
        print(f"  🎯 여분 문제 생성 중... (객관식: {extra_objective}, 주관식: {extra_subjective})")
        
        try:
            # 키워드 기반 특화 문제 생성
            keywords = document_test_plan.get('keywords', [])[:5]  # 상위 5개 키워드 사용
            
            # 키워드를 강조한 특별 프롬프트로 문제 생성
            extra_questions = generate_question_with_test_plan(
                messages=chunk["messages"],
                source=chunk["metadata"].get("source", "unknown"),
                page=f"키워드특화_{chunk['metadata'].get('page', 'N/A')}",
                num_objective=extra_objective,
                num_subjective=extra_subjective,
                total_test_plan=total_test_plan,
                document_test_plan=document_test_plan,
            )
            
            # 여분 문제임을 표시
            for q in extra_questions:
                if 'test_context' not in q:
                    q['test_context'] = {}
                q['test_context']['is_extra_question'] = True
                q['test_context']['focus_keywords'] = keywords
            
            return extra_questions
        
        except Exception as e:
            print(f"    ⚠️ 여분 문제 생성 실패: {e}")
            return []

    def _load_test_plan(self, file_path: str) -> Dict:
        """Test Plan JSON 파일을 로드"""
        try:
            import json
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Test Plan 로드 실패 ({file_path}): {e}")
            return {}

    def generate_questions_for_blocks(
        self, blocks: List[Dict], num_objective: int = 3, num_subjective: int = 3, 
        difficulty: str = "NORMAL", total_test_plan: Dict = None, document_test_plan: Dict = None
    ) -> List[Dict]:
        """
        블록들에 대해 GPT-4 Vision으로 질문 생성

        Args:
            blocks: 문서 블록들
            num_objective: 객관식 문제 수
            num_subjective: 주관식 문제 수

        Returns:
            List[Dict]: 질문이 추가된 블록들
        """
        print("🤖 Gemini 2.5 Pro 질문 생성 중...")

        try:
            # 블록들을 청킹하여 Gemini 2.5 Pro 메시지 생성
            vision_chunks = self._blocks_to_vision_chunks(blocks)

            questions_generated = 0
            total_questions_target = num_objective + num_subjective

            for i, chunk in enumerate(vision_chunks):
                if questions_generated >= total_questions_target:
                    break

                print(f"  📝 청크 {i+1}/{len(vision_chunks)} 질문 생성 중...")

                # 남은 질문 수 계산
                remaining_obj = max(
                    0,
                    num_objective
                    - len(
                        [
                            q
                            for b in blocks
                            for q in b.get("questions", [])
                            if q.get("type") == "OBJECTIVE"
                        ]
                    ),
                )
                remaining_subj = max(
                    0,
                    num_subjective
                    - len(
                        [
                            q
                            for b in blocks
                            for q in b.get("questions", [])
                            if q.get("type") == "SUBJECTIVE"
                        ]
                    ),
                )

                if remaining_obj == 0 and remaining_subj == 0:
                    break

                # 청크별 질문 수 분배
                chunk_obj = min(
                    remaining_obj, max(0, remaining_obj // max(1, len(vision_chunks) - i))
                ) if remaining_obj > 0 else 0
                chunk_subj = min(
                    remaining_subj, max(0, remaining_subj // max(1, len(vision_chunks) - i))
                ) if remaining_subj > 0 else 0
                
                # 마지막 청크에서 남은 문제들 모두 할당
                if i == len(vision_chunks) - 1:
                    chunk_obj = remaining_obj
                    chunk_subj = remaining_subj

                if chunk_obj == 0 and chunk_subj == 0:
                    continue

                try:
                    # Gemini 2.5 Pro로 질문 생성 (테스트 계획 활용)
                    if total_test_plan or document_test_plan:
                        questions = generate_question_with_test_plan(
                            messages=chunk["messages"],
                            source=chunk["metadata"].get("source", "unknown"),
                            page=str(chunk["metadata"].get("page", "N/A")),
                            num_objective=chunk_obj,
                            num_subjective=chunk_subj,
                            difficulty=difficulty,
                            total_test_plan=total_test_plan,
                            document_test_plan=document_test_plan,
                        )
                    else:
                        questions = generate_question(
                            messages=chunk["messages"],
                            source=chunk["metadata"].get("source", "unknown"),
                            page=str(chunk["metadata"].get("page", "N/A")),
                            num_objective=chunk_obj,
                            num_subjective=chunk_subj,
                            difficulty=difficulty,
                        )

                    # 첫 번째 블록에 질문 추가 (청크 대표)
                    if chunk["block_indices"] and questions:
                        first_block_idx = chunk["block_indices"][0]
                        if "questions" not in blocks[first_block_idx]:
                            blocks[first_block_idx]["questions"] = []
                        blocks[first_block_idx]["questions"].extend(questions)
                        questions_generated += len(questions)

                        print(f"    ✅ {len(questions)}개 질문 생성")

                except Exception as e:
                    print(f"    ⚠️ 청크 {i+1} 질문 생성 실패: {e}")
                    continue

            total_generated = sum(len(b.get("questions", [])) for b in blocks)
            print(f"✅ 총 {total_generated}개 질문 생성 완료")

        except Exception as e:
            print(f"❌ 질문 생성 중 오류: {e}")

        return blocks

    def _blocks_to_vision_chunks(
        self, blocks: List[Dict], max_chunk_size: int = 15000
    ) -> List[Dict]:
        """블록들을 Gemini 2.5 Pro API용 청크로 변환"""
        chunks = []
        current_chunk = {
            "messages": [],
            "metadata": {"pages": set(), "source": "document_analyzer"},
            "block_indices": [],
            "current_length": 0,
        }

        def save_current_chunk():
            if current_chunk["messages"]:
                final_metadata = current_chunk["metadata"].copy()
                final_metadata["pages"] = sorted(list(final_metadata["pages"]))
                final_metadata["page"] = (
                    final_metadata["pages"][0] if final_metadata["pages"] else 1
                )

                chunks.append(
                    {
                        "messages": current_chunk["messages"].copy(),
                        "metadata": final_metadata,
                        "block_indices": current_chunk["block_indices"].copy(),
                    }
                )

            current_chunk["messages"].clear()
            current_chunk["metadata"] = {"pages": set(), "source": "document_analyzer"}
            current_chunk["block_indices"].clear()
            current_chunk["current_length"] = 0

        for block_idx, block in enumerate(blocks):
            block_type = block.get("type", "unknown")
            content = block.get("content", "")
            metadata = block.get("metadata", {})
            page_no = metadata.get("page", 1)

            # 블록을 메시지로 변환
            message_content = None
            text_length = 0

            if block_type in ["paragraph", "heading", "section"]:
                text_content = str(content) if content else ""
                if text_content.strip():
                    if block_type == "heading":
                        text_content = f"# {text_content}"
                    elif block_type == "section":
                        text_content = f"## {text_content}"

                    message_content = {"type": "text", "text": text_content}
                    text_length = len(text_content)

            elif block_type == "table":
                # 표를 텍스트로 변환
                if isinstance(content, dict) and "data" in content:
                    table_text = self._format_table_as_text(content)
                    message_content = {"type": "text", "text": f"[Table]\n{table_text}"}
                    text_length = len(table_text)

            elif block_type == "image":
                # 이미지 파일 읽기
                image_path = os.path.join(self.image_save_dir, block.get("path", ""))
                if os.path.exists(image_path):
                    try:
                        with open(image_path, "rb") as f:
                            encoded = base64.b64encode(f.read()).decode("utf-8")
                        message_content = {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{encoded}"},
                        }
                        text_length = 1000  # 이미지는 고정 길이로 계산
                    except Exception as e:
                        print(f"이미지 읽기 실패 {image_path}: {e}")
                        continue

            # 청크 크기 확인 및 저장
            if message_content:
                if (
                    current_chunk["current_length"] + text_length > max_chunk_size
                    and current_chunk["messages"]
                ):
                    save_current_chunk()

                current_chunk["messages"].append(message_content)
                current_chunk["metadata"]["pages"].add(page_no)
                current_chunk["block_indices"].append(block_idx)
                current_chunk["current_length"] += text_length

        # 마지막 청크 저장
        save_current_chunk()

        return chunks

    def _format_table_as_text(self, table_data: Dict) -> str:
        """표 데이터를 텍스트로 변환"""
        if not isinstance(table_data, dict) or "data" not in table_data:
            return str(table_data)

        headers = table_data.get("headers", [])
        data = table_data.get("data", [])

        if not data:
            return ""

        table_str = ""
        if headers:
            table_str += " | ".join(str(h) for h in headers) + "\n"
            table_str += "|" + "|".join([":---:"] * len(headers)) + "|\n"

        for row in data:
            table_str += " | ".join(str(cell) for cell in row) + "\n"

        return table_str.strip()


def generate_questions_for_document(
    blocks: List[Dict],
    image_save_dir: str = "data/images",
    num_objective: int = 3,
    num_subjective: int = 3,
) -> List[Dict]:
    """
    편의 함수: 문서 블록들에 대해 질문 생성

    Args:
        blocks: 문서 블록들
        image_save_dir: 이미지 저장 디렉토리
        num_objective: 객관식 문제 수
        num_subjective: 주관식 문제 수

    Returns:
        List[Dict]: 질문이 추가된 블록들
    """
    generator = QuestionGenerator(image_save_dir)
    return generator.generate_questions_for_blocks(
        blocks, num_objective, num_subjective
    )


def generate_questions_with_test_plans(
    blocks: List[Dict],
    image_save_dir: str = "data/images",
    num_objective: int = 3,
    num_subjective: int = 3,
    total_test_plan_path: str = None,
    document_test_plan_path: str = None,
    source_document_name: str = None,
) -> List[Dict]:
    """
    편의 함수: Test Plan을 활용하여 문서 블록들에 대해 질문 생성

    Args:
        blocks: 문서 블록들
        image_save_dir: 이미지 저장 디렉토리
        num_objective: 객관식 문제 수 (document_test_plan의 추천값으로 대체 가능)
        num_subjective: 주관식 문제 수 (document_test_plan의 추천값으로 대체 가능)
        total_test_plan_path: 전체 테스트 계획 JSON 파일 경로
        document_test_plan_path: 문서별 테스트 계획 JSON 파일 경로
        source_document_name: 소스 문서명 (document_test_plan에서 찾기 위함)

    Returns:
        List[Dict]: 질문이 추가된 블록들 (기본 문제 + 여분 2문제씩)
    """
    generator = QuestionGenerator(image_save_dir)
    return generator.generate_questions_with_test_plans(
        blocks, num_objective, num_subjective, 
        total_test_plan_path, document_test_plan_path, source_document_name
    )
