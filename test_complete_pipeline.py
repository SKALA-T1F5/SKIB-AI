#!/usr/bin/env python3
"""
통합 PDF 처리 파이프라인 테스트
- 통합 파서 (Docling + 선택적 요소 추출)
- 키워드 추출 및 요약 (JSON 출력)
- 결과 분석 및 리포트 생성

사용법:
python test_complete_pipeline.py
"""

import os
import json
import time
from typing import List, Dict
from src.agents.question_generator.unified_parser import parse_pdf_unified
from src.agents.question_generator.keyword_summary import extract_keywords_and_summary
from src.agents.question_generator.change_name import normalize_collection_name


def test_document(pdf_path: str, document_name: str) -> Dict:
    """개별 문서 테스트"""
    print(f"\n{'='*60}")
    print(f"🔄 {document_name} 테스트 시작")
    print(f"📄 파일: {pdf_path}")
    print(f"{'='*60}")
    
    if not os.path.exists(pdf_path):
        print(f"❌ 파일을 찾을 수 없습니다: {pdf_path}")
        return None
    
    start_time = time.time()
    
    try:
        # 1. 통합 파서 실행
        print("\n1️⃣ 통합 파서 실행 중...")
        source_file = os.path.basename(pdf_path)
        collection_name = os.path.splitext(source_file)[0]
        
        normalized_name = normalize_collection_name(collection_name)
        blocks = parse_pdf_unified(pdf_path, normalized_name)
        
        # 2. 블록 분석
        text_blocks = [b for b in blocks if b.get('type') in ['paragraph', 'section', 'heading']]
        table_blocks = [b for b in blocks if b.get('type') == 'table']
        image_blocks = [b for b in blocks if b.get('type') == 'image']
        
        print(f"✅ 파서 완료: 총 {len(blocks)}개 블록")
        print(f"   - 텍스트: {len(text_blocks)}개")
        print(f"   - 표: {len(table_blocks)}개")
        print(f"   - 이미지: {len(image_blocks)}개")
        
        # 3. 키워드 추출 및 요약
        print("\n2️⃣ 키워드 추출 및 요약 중...")
        keywords_result = extract_keywords_and_summary(blocks, source_file)
        
        # 4. JSON 파일 저장
        output_dir = "data/outputs"
        os.makedirs(output_dir, exist_ok=True)
        
        output_filename = f"{normalized_name}.json"
        output_path = os.path.join(output_dir, output_filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(keywords_result, f, ensure_ascii=False, indent=2)
        
        processing_time = time.time() - start_time
        
        # 5. 결과 요약
        content_analysis = keywords_result.get('content_analysis', {})
        
        result = {
            "document_name": document_name,
            "file_path": pdf_path,
            "processing_time": round(processing_time, 2),
            "extraction_stats": {
                "total_blocks": len(blocks),
                "text_blocks": len(text_blocks),
                "table_blocks": len(table_blocks),
                "image_blocks": len(image_blocks)
            },
            "content_summary": {
                "summary": content_analysis.get('summary', '')[:100] + "..." if content_analysis.get('summary') else '',
                "main_topics_count": len(content_analysis.get('main_topics', [])),
                "key_concepts_count": len(content_analysis.get('key_concepts', [])),
                "technical_terms_count": len(content_analysis.get('technical_terms', []))
            },
            "output_file": output_path,
            "image_directory": f"data/images/{normalized_name}"
        }
        
        print(f"✅ 키워드 추출 완료")
        print(f"💾 결과 저장: {output_path}")
        print(f"⏱️  처리 시간: {processing_time:.2f}초")
        
        return result
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return {
            "document_name": document_name,
            "file_path": pdf_path,
            "error": str(e),
            "processing_time": time.time() - start_time
        }


def print_test_results(results: List[Dict]):
    """테스트 결과 출력"""
    print(f"\n{'='*80}")
    print("📊 통합 테스트 결과 요약")
    print(f"{'='*80}")
    
    successful_tests = [r for r in results if r and 'error' not in r]
    failed_tests = [r for r in results if r and 'error' in r]
    
    print(f"✅ 성공: {len(successful_tests)}개")
    print(f"❌ 실패: {len(failed_tests)}개")
    print(f"⏱️  평균 처리 시간: {sum(r['processing_time'] for r in successful_tests) / len(successful_tests):.2f}초" if successful_tests else "")
    
    if successful_tests:
        print(f"\n📋 성공한 테스트:")
        for result in successful_tests:
            stats = result.get('extraction_stats', {})
            content = result.get('content_summary', {})
            
            print(f"\n🔹 {result['document_name']}")
            print(f"   블록: {stats.get('total_blocks', 0)}개 (텍스트:{stats.get('text_blocks', 0)}, 표:{stats.get('table_blocks', 0)}, 이미지:{stats.get('image_blocks', 0)})")
            print(f"   키워드: 주제 {content.get('main_topics_count', 0)}개, 개념 {content.get('key_concepts_count', 0)}개, 용어 {content.get('technical_terms_count', 0)}개")
            print(f"   요약: {content.get('summary', '요약 없음')}")
            print(f"   출력: {result.get('output_file', 'N/A')}")
            print(f"   처리시간: {result['processing_time']}초")
    
    if failed_tests:
        print(f"\n❌ 실패한 테스트:")
        for result in failed_tests:
            print(f"   - {result['document_name']}: {result.get('error', '알 수 없는 오류')}")


def main():
    """메인 테스트 함수"""
    print("🚀 통합 PDF 처리 파이프라인 테스트 시작")
    print("=" * 60)
    
    # 테스트할 문서 목록
    test_documents = [
        {
            "name": "FBS UI 정의서",
            "path": "data/raw_docs/FBS_To-Be UI정의서_펌뱅킹_v0.66.pdf"
        }
    ]
    
    # 결과 저장
    all_results = []
    total_start_time = time.time()
    
    # 각 문서 테스트 실행
    for doc in test_documents:
        result = test_document(doc["path"], doc["name"])
        if result:
            all_results.append(result)
    
    total_time = time.time() - total_start_time
    
    # 종합 결과 출력
    print_test_results(all_results)
    
    # 종합 결과 JSON 저장
    summary_result = {
        "test_info": {
            "test_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_processing_time": round(total_time, 2),
            "documents_tested": len(test_documents)
        },
        "results": all_results
    }
    
    summary_path = "data/outputs/complete_pipeline_test_summary.json"
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary_result, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 종합 결과 저장: {summary_path}")
    print(f"⏱️  전체 처리 시간: {total_time:.2f}초")
    print("\n🎉 통합 테스트 완료!")


if __name__ == "__main__":
    main()