import logging

"""
각 문서에 대해 주요 키워드 추출 및 요약을 수행하고 JSON 형태로 출력하는 모듈입니다.
Docling으로 파싱된 블록들을 분석하여 문서의 핵심 내용을 추출합니다.
"""

import json
from typing import Dict, List

from langsmith import traceable
from langsmith.wrappers import wrap_openai
from openai import OpenAI

from config.settings import settings

openai_client = wrap_openai(OpenAI(api_key=settings.api_key))
logger = logging.getLogger(__name__)


def extract_keywords_and_summary(blocks: List[Dict], source_file: str) -> Dict:
    """
    Docling 블록들에서 키워드 추출 및 요약을 수행합니다.

    Args:
        blocks: Docling 파서에서 생성된 블록 리스트
        source_file: 원본 파일명

    Returns:
        Dict: 키워드, 요약, 메타데이터가 포함된 딕셔너리
    """
    # 텍스트 블록들에서 내용 추출
    text_content = []
    total_pages = set()
    sections = []

    for block in blocks:
        block_type = block.get("type", "")
        page_no = block.get("metadata", {}).get("page")

        if page_no:
            total_pages.add(page_no)

        if block_type in ["paragraph", "heading"]:  # heading 타입 추가
            content = block.get("content", "").strip()
            if content:
                text_content.append(content)
        elif block_type == "section":
            title = block.get("title", "").strip()
            if title:
                sections.append(title)

    # 전체 텍스트 결합
    combined_text = "\n".join(text_content)

    # LLM을 사용한 키워드 추출 및 요약
    llm_result = _extract_keywords_summary_with_llm(combined_text, source_file)

    # 결과 구성
    result = {
        "document_info": {"filename": source_file},
        "content_analysis": {
            "summary": llm_result.get("summary", ""),
            "main_topics": llm_result.get("main_topics", []),
            "key_concepts": llm_result.get("key_concepts", []),
            "technical_terms": llm_result.get("technical_terms", []),
        },
    }

    return result


@traceable(
    run_type="chain",
    name="Extract Keywords Summary with LLM",
    metadata={"agent_type": "document_analyzer"},
)
def _extract_keywords_summary_with_llm(text: str, filename: str) -> Dict:
    """
    GPT-4를 사용하여 텍스트에서 키워드 추출 및 요약 수행
    """
    # 텍스트 길이 확인 및 제한
    if not text or len(text.strip()) < 50:
        logger.warning("⚠️ 텍스트가 너무 짧거나 비어있습니다.")
        return {
            "summary": "텍스트가 부족하여 요약할 수 없습니다.",
            "main_topics": [],
            "key_concepts": [],
            "technical_terms": [],
        }

    # 텍스트가 너무 긴 경우 분할 처리 (GPT-4 토큰 제한 고려)
    max_length = 4000  # 더 안전한 길이로 축소
    if len(text) > max_length:
        # 앞부분과 뒷부분 일부 사용하여 대표성 확보
        front_part = text[: max_length // 2]
        back_part = text[-(max_length // 2) :]
        text = front_part + "\n\n[중간 내용 생략...]\n\n" + back_part
        logger.info(f"📝 텍스트 길이 조정: 원본 {len(text)}자 → 압축 {len(text)}자")

    prompt = f"""
문서 "{filename}"의 내용을 분석하여 다음 정보를 JSON 형식으로 추출해주세요:

1. summary: 문서의 핵심 내용을 2-3문장으로 요약
2. main_topics: 문서의 주요 주제/토픽 (최대 5개)
3. key_concepts: 핵심 개념이나 용어 (최대 10개)
4. technical_terms: 전문 용어나 기술 용어 (최대 8개)

응답은 반드시 다음 JSON 형식으로만 제공해주세요:

{{
    "summary": "문서 요약 내용",
    "main_topics": ["주제1", "주제2", "주제3"],
    "key_concepts": ["개념1", "개념2", "개념3"],
    "technical_terms": ["용어1", "용어2", "용어3"]
}}

분석할 문서 내용:
{text}
"""

    try:
        logger.info(f"🤖 GPT-4 분석 시작... (텍스트 길이: {len(text)}자)")
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1000,  # 토큰 수 줄임
            timeout=30,  # 30초 타임아웃 설정
        )
        logger.info("✅ GPT-4 분석 완료")

        raw_content = response.choices[0].message.content
        if raw_content is None:
            logger.error("❌ GPT-4 응답 내용이 비어있습니다")
            return {
                "summary": "GPT-4 응답 오류",
                "main_topics": [],
                "key_concepts": [],
                "technical_terms": [],
            }

        raw_content = raw_content.strip()

        # JSON 파싱
        try:
            logger.debug(f"📄 응답 내용 미리보기: {raw_content[:100]}...")

            # 코드 블록 제거
            if "```json" in raw_content:
                raw_content = raw_content.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_content:
                raw_content = raw_content.split("```")[1].split("```")[0].strip()

            result = json.loads(raw_content)
            logger.info("✅ JSON 파싱 성공")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"❌ LLM JSON 파싱 실패: {e}")
            logger.debug(f"원본 응답: {raw_content}")
            return {
                "summary": "JSON 파싱 실패로 요약 생성 불가",
                "main_topics": [],
                "key_concepts": [],
                "technical_terms": [],
            }

    except Exception as e:
        logger.error(f"LLM 키워드 추출 실패: {e}")
        return {
            "summary": "요약 생성 실패",
            "main_topics": [],
            "key_concepts": [],
            "technical_terms": [],
        }
