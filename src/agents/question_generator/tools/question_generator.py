"""
질문 생성 도구
- GPT-4 Vision을 사용한 자동 질문 생성
- 블록을 Vision API용 청크로 변환
- 객관식/주관식 문제 생성
"""

import base64
import json
from typing import Dict, List

from dotenv import load_dotenv
from openai import OpenAI

from .prompt import get_vision_prompt

# 환경 변수 로드
load_dotenv(override=True)
api_key = os.getenv("OPENAI_API_KEY")
openai_client = OpenAI(api_key=api_key)
# google_api_key = os.getenv("GOOGLE_API_KEY")
# genai.configure(api_key=google_api_key)


def generate_question(
    messages: List[Dict],
    source: str,
    page: str,
    num_objective: int = 1,
    num_subjective: int = 1,
    difficulty: str = "NORMAL",
    keywords: List[str] = None,
    main_topics: List[str] = None,
    test_config: Dict = None,
) -> List[Dict]:
    """
    GPT-4 Vision을 사용하여 질문을 생성하는 함수 (향상된 기능)

    Args:
        messages: Vision API 메시지 배열 (텍스트 및 이미지 포함)
        source: 문서 소스 파일명
        page: 페이지 번호
        num_objective: 객관식 문제 수
        num_subjective: 주관식 문제 수
        difficulty: 난이도 (EASY, NORMAL, HARD)
        keywords: 키워드 목록 (문제 생성 시 활용)
        main_topics: 주요 주제 목록
        test_config: 테스트 설정

    Returns:
        List[Dict]: 생성된 질문 목록
    """
    try:
        # Vision API용 프롬프트 생성 (키워드와 주제 정보 포함)
        system_prompt = get_vision_prompt(
            source,
            page,
            difficulty,
            num_objective,
            num_subjective,
            keywords,
            main_topics,
            test_config,
        )

        # 메시지 구성
        api_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": messages},
        ]

        print(
            f"  🤖 GPT-4 Vision 호출 중... (객관식: {num_objective}, 주관식: {num_subjective})"
        )

        # GPT-4 Vision API 호출
        response = openai_client.chat.completions.create(
            model="gpt-4o",  # Vision 지원 모델
            messages=api_messages,
            temperature=0.7,
            max_tokens=2000,
            timeout=60,
        )

        raw_content = response.choices[0].message.content.strip()
        print(f"  📄 응답 내용 미리보기: {raw_content[:100]}...")

        # JSON 파싱
        try:
            # 코드 블록 제거
            if "```json" in raw_content:
                raw_content = raw_content.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_content:
                raw_content = raw_content.split("```")[1].split("```")[0].strip()

            questions = json.loads(raw_content)

            # 리스트인지 확인
            if not isinstance(questions, list):
                print(f"⚠️ 응답이 리스트가 아닙니다: {type(questions)}")
                return []

            print(f"  ✅ {len(questions)}개 질문 파싱 성공")
            return questions

        except json.JSONDecodeError as e:
            print(f"  ❌ JSON 파싱 실패: {e}")
            print(f"  원본 응답: {raw_content}")
            return []

    except Exception as e:
        print(f"  ❌ 질문 생성 실패: {e}")
        import traceback

        print(f"  📄 상세 오류: {traceback.format_exc()}")
        return []


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
    """
    질문 생성 클래스

    GPT-4 Vision을 사용하여 문서 블록들로부터 자동으로 질문을 생성합니다.
    텍스트, 이미지, 표를 모두 처리할 수 있습니다.
    """

    def __init__(self, image_save_dir: str = "data/images"):
        """
        QuestionGenerator 초기화

        Args:
            image_save_dir: 이미지 파일이 저장된 디렉토리 경로
        """
        self.image_save_dir = image_save_dir

    def generate_questions_for_blocks(
        self,
        blocks: List[Dict],
        num_objective: int = 3,
        num_subjective: int = 3,
        keywords: List[str] = None,
        main_topics: List[str] = None,
        summary: str = "",
        test_config: Dict = None,
    ) -> List[Dict]:
        """
        블록들에 대해 GPT-4 Vision으로 질문 생성 (향상된 기능)

        Args:
            blocks: 문서 블록들
            num_objective: 객관식 문제 수
            num_subjective: 주관식 문제 수
            keywords: 키워드 목록 (문제 생성 시 활용)
            main_topics: 주요 주제 목록
            summary: 문서 요약
            test_config: 테스트 설정

        Returns:
            List[Dict]: 질문이 추가된 블록들
        """
        print("🤖 GPT-4 Vision 질문 생성 중...")

        try:
            # 블록들을 청킹하여 GPT-4 Vision 메시지 생성
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
                    remaining_obj, max(1, remaining_obj // (len(vision_chunks) - i))
                )
                chunk_subj = min(
                    remaining_subj, max(1, remaining_subj // (len(vision_chunks) - i))
                )

                if chunk_obj == 0 and chunk_subj == 0:
                    continue

                try:
                    # GPT-4 Vision으로 질문 생성 (키워드와 주제 활용)
                    questions = generate_question(
                        messages=chunk["messages"],
                        source=chunk["metadata"].get("source", "unknown"),
                        page=str(chunk["metadata"].get("page", "N/A")),
                        num_objective=chunk_obj,
                        num_subjective=chunk_subj,
                        keywords=keywords or [],
                        main_topics=main_topics or [],
                        test_config=test_config,
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
        """
        블록들을 GPT-4 Vision API용 청크로 변환

        Args:
            blocks: 문서 블록들
            max_chunk_size: 최대 청크 크기 (토큰 제한)

        Returns:
            List[Dict]: Vision API용 청크들
        """
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
        """
        표 데이터를 텍스트로 변환 (마크다운 형식)

        Args:
            table_data: 표 데이터 딕셔너리

        Returns:
            str: 마크다운 형식의 표 텍스트
        """
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
