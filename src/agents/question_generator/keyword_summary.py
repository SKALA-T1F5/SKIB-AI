"""
각 문서에 대해 주요 키워드 추출 및 요약을 수행하고 JSON 형태로 출력하는 모듈입니다.
Docling으로 파싱된 블록들을 분석하여 문서의 핵심 내용을 추출합니다.
"""

import json
import os
from typing import List, Dict
from openai import OpenAI
from dotenv import load_dotenv
from src.agents.question_generator.change_name import normalize_collection_name

# 환경 변수 로드
load_dotenv(override=True)
api_key = os.getenv("OPENAI_API_KEY")
openai_client = OpenAI(api_key=api_key)


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
        "document_info": {
            "filename": source_file
        },
        "content_analysis": {
            "summary": llm_result.get("summary", ""),
            "main_topics": llm_result.get("main_topics", []),
            "key_concepts": llm_result.get("key_concepts", []),
            "technical_terms": llm_result.get("technical_terms", [])
        }
    }
    
    return result


def _extract_keywords_summary_with_llm(text: str, filename: str) -> Dict:
    """
    GPT-4를 사용하여 텍스트에서 키워드 추출 및 요약 수행
    """
    # 텍스트 길이 확인 및 제한
    if not text or len(text.strip()) < 50:
        print("⚠️ 텍스트가 너무 짧거나 비어있습니다.")
        return {
            "summary": "텍스트가 부족하여 요약할 수 없습니다.",
            "main_topics": [],
            "key_concepts": [],
            "technical_terms": []
        }
    
    # 텍스트가 너무 긴 경우 분할 처리 (GPT-4 토큰 제한 고려)
    max_length = 4000  # 더 안전한 길이로 축소
    if len(text) > max_length:
        # 앞부분과 뒷부분 일부 사용하여 대표성 확보
        front_part = text[:max_length//2]
        back_part = text[-(max_length//2):]
        text = front_part + "\n\n[중간 내용 생략...]\n\n" + back_part
        print(f"📝 텍스트 길이 조정: 원본 {len(text)}자 → 압축 {len(text)}자")
    
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
        print(f"🤖 GPT-4 분석 시작... (텍스트 길이: {len(text)}자)")
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1000,  # 토큰 수 줄임
            timeout=30  # 30초 타임아웃 설정
        )
        print("✅ GPT-4 분석 완료")
        
        raw_content = response.choices[0].message.content.strip()
        
        # JSON 파싱
        try:
            print(f"📄 응답 내용 미리보기: {raw_content[:100]}...")
            
            # 코드 블록 제거
            if "```json" in raw_content:
                raw_content = raw_content.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_content:
                raw_content = raw_content.split("```")[1].split("```")[0].strip()
            
            result = json.loads(raw_content)
            print("✅ JSON 파싱 성공")
            return result
            
        except json.JSONDecodeError as e:
            print(f"❌ LLM JSON 파싱 실패: {e}")
            print(f"원본 응답: {raw_content}")
            return {
                "summary": "JSON 파싱 실패로 요약 생성 불가",
                "main_topics": [],
                "key_concepts": [],
                "technical_terms": []
            }
            
    except Exception as e:
        print(f"LLM 키워드 추출 실패: {e}")
        return {
            "summary": "요약 생성 실패",
            "main_topics": [],
            "key_concepts": [],
            "technical_terms": []
        }




# 테스트용 실행 코드
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        from src.agents.question_generator.unified_parser import parse_pdf_unified
        
        pdf_path = sys.argv[1]
        output_dir = sys.argv[2] if len(sys.argv) > 2 else "data/outputs"
        
        if os.path.exists(pdf_path):
            # 출력 디렉토리 생성
            os.makedirs(output_dir, exist_ok=True)
            
            # PDF 파싱 (통합 파서 사용)
            source_file = os.path.basename(pdf_path)
            collection_name = os.path.splitext(source_file)[0]
            
            print(f"📄 PDF 파싱 중: {source_file}")
            blocks = parse_pdf_unified(pdf_path, collection_name)
            
            # 키워드 추출 및 요약
            print(f"🔍 키워드 추출 및 요약 중...")
            result = extract_keywords_and_summary(blocks, source_file)
            
            # JSON 파일로 저장 (컬렉션명 정규화)
            normalized_name = normalize_collection_name(collection_name)
            output_filename = f"{normalized_name}_keywords_summary.json"
            output_path = os.path.join(output_dir, output_filename)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 키워드 및 요약 완료!")
            print(f"💾 결과 저장: {output_path}")
            print()
            print("📊 결과 요약:")
            print(f"  - 파일명: {result['document_info']['filename']}")
            print(f"  - 요약: {result['content_analysis']['summary'][:100]}...")
            print(f"  - 주요 주제: {len(result['content_analysis']['main_topics'])}개")
            print(f"  - 핵심 개념: {len(result['content_analysis']['key_concepts'])}개")
            print(f"  - 기술 용어: {len(result['content_analysis']['technical_terms'])}개")
            
        else:
            print(f"❌ 파일을 찾을 수 없습니다: {pdf_path}")
    else:
        print("사용법: python keyword_summary.py <pdf_path> [output_dir]")
        print("예시: python keyword_summary.py 'file.pdf' 'outputs/'")
        print("기본 출력 디렉토리: data/outputs")