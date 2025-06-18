"""
ChromaDB 사용 예제
"""

import sys
import os
from pathlib import Path

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from db.vectorDB.chromaDB import (
    get_client,
    upload_documents,
    search_similar,
    list_collections,
    get_collection_info
)
from db.vectorDB.chromaDB.pipeline import ChromaDBPipeline


def example_basic_usage():
    """기본 사용법 예제"""
    print("🔧 ChromaDB 기본 사용법")
    print("=" * 50)
    
    # 1. 클라이언트 연결 테스트
    client = get_client()
    if client.test_connection():
        print("✅ ChromaDB 연결 성공")
    else:
        print("❌ ChromaDB 연결 실패")
        return
    
    # 2. 컬렉션 목록 확인
    collections = list_collections()
    print(f"📂 현재 컬렉션: {collections}")
    
    # 3. 테스트 데이터 업로드
    test_blocks = [
        {
            "content": "ChromaDB는 오픈소스 벡터 데이터베이스입니다.",
            "type": "text",
            "metadata": {"section": "intro", "page": 1}
        },
        {
            "content": "벡터 검색을 통해 유사한 문서를 찾을 수 있습니다.",
            "type": "text", 
            "metadata": {"section": "features", "page": 1}
        }
    ]
    
    collection_name = "test_example"
    uploaded_count = upload_documents(test_blocks, collection_name, "example.txt")
    print(f"📄 업로드 완료: {uploaded_count}개")
    
    # 4. 검색 테스트
    results = search_similar("벡터 검색", collection_name, n_results=2)
    print(f"🔍 검색 결과:")
    for i, result in enumerate(results, 1):
        print(f"  [{i}] 유사도: {result['similarity']:.3f}")
        print(f"      내용: {result['content']}")
    
    # 5. 컬렉션 정보 확인
    info = get_collection_info(collection_name)
    print(f"📊 컬렉션 정보: {info['count']}개 문서")


def example_document_analyzer_integration():
    """DocumentAnalyzer와의 통합 예제"""
    print("\n🔗 DocumentAnalyzer 통합 예제")
    print("=" * 50)
    
    try:
        from src.agents.document_analyzer.agent import DocumentAnalyzerAgent
        
        # PDF 파일 경로
        pdf_path = "data/raw_docs/Process 흐름도_sample_250527.pdf"
        if not os.path.exists(pdf_path):
            print(f"❌ 테스트 파일이 없습니다: {pdf_path}")
            return
        
        # DocumentAnalyzer로 문서 분석
        collection_name = "example_integration"
        analyzer = DocumentAnalyzerAgent(collection_name, auto_upload_chromadb=True)
        
        print(f"📋 문서 분석 시작: {pdf_path}")
        result = analyzer.analyze_document(pdf_path, extract_keywords=True)
        
        print(f"📊 분석 결과:")
        print(f"  상태: {result.get('processing_status')}")
        print(f"  총 블록: {result.get('total_blocks')}개")
        print(f"  ChromaDB 업로드: {'✅' if result.get('chromadb_uploaded') else '❌'}")
        print(f"  업로드된 청크: {result.get('chromadb_upload_count')}개")
        
        # 업로드된 데이터로 검색 테스트
        if result.get('chromadb_uploaded'):
            print(f"\n🔍 업로드된 데이터 검색:")
            results = search_similar("프로세스", collection_name, n_results=3)
            
            for i, res in enumerate(results, 1):
                print(f"  [{i}] 유사도: {res['similarity']:.3f}")
                print(f"      {res['content'][:60]}...")
        
    except ImportError:
        print("❌ DocumentAnalyzer를 불러올 수 없습니다")
    except Exception as e:
        print(f"❌ 통합 예제 실패: {e}")


def example_pipeline_usage():
    """파이프라인 사용 예제"""
    print("\n🚀 ChromaDB 파이프라인 예제")
    print("=" * 50)
    
    # 파이프라인 초기화
    pipeline = ChromaDBPipeline()
    
    # 테스트 문서 블록
    document_blocks = [
        {
            "content": "파이프라인 테스트 문서입니다.",
            "type": "text",
            "metadata": {"section": "test", "page": 1}
        },
        {
            "content": "ChromaDB 파이프라인의 기능을 시연합니다.",
            "type": "text",
            "metadata": {"section": "demo", "page": 1}
        }
    ]
    
    # 문서 처리 및 업로드
    collection_name = "pipeline_example"
    result = pipeline.process_and_upload_document(
        document_blocks, 
        collection_name, 
        "pipeline_test.txt",
        recreate_collection=True
    )
    
    print(f"📄 파이프라인 처리 결과:")
    print(f"  상태: {result['status']}")
    print(f"  업로드: {result['uploaded_count']}/{result['total_blocks']}개")
    
    # 검색 및 분석
    search_result = pipeline.search_and_analyze(
        "파이프라인", 
        collection_name, 
        n_results=2
    )
    
    print(f"🔍 검색 및 분석 결과:")
    print(f"  결과 수: {search_result['result_count']}개")
    if search_result.get('analysis'):
        analysis = search_result['analysis']
        print(f"  평균 유사도: {analysis['avg_similarity']:.3f}")
    
    # 파이프라인 상태 확인
    status = pipeline.get_pipeline_status()
    print(f"📊 파이프라인 상태: {status.get('client_status')}")


def example_advanced_search():
    """고급 검색 예제"""
    print("\n🔍 고급 검색 예제")
    print("=" * 50)
    
    from db.vectorDB.chromaDB.search import ChromaDBSearcher
    
    # 기존 컬렉션 사용
    collections = list_collections()
    if not collections:
        print("❌ 검색할 컬렉션이 없습니다")
        return
    
    collection_name = collections[0]
    searcher = ChromaDBSearcher()
    
    print(f"📂 검색 대상 컬렉션: {collection_name}")
    
    # 1. 메타데이터 기반 검색
    metadata_results = searcher.search_by_metadata(
        collection_name,
        where={"chunk_type": "heading"}
    )
    print(f"📋 헤딩 타입 검색: {len(metadata_results)}개")
    
    # 2. 타입별 검색
    text_results = searcher.search_by_type(collection_name, "text")
    print(f"📝 텍스트 타입 검색: {len(text_results)}개")
    
    # 3. 하이브리드 검색
    hybrid_results = searcher.hybrid_search(
        "프로세스",
        collection_name,
        n_results=3,
        metadata_filter={"chunk_type": "heading"},
        min_similarity=0.5
    )
    print(f"🔀 하이브리드 검색: {len(hybrid_results)}개")
    
    for i, result in enumerate(hybrid_results, 1):
        print(f"  [{i}] {result['content'][:50]}... (유사도: {result['similarity']:.3f})")


def main():
    """모든 예제 실행"""
    print("🎯 ChromaDB 사용 예제")
    print("=" * 80)
    
    try:
        # 기본 사용법
        example_basic_usage()
        
        # DocumentAnalyzer 통합
        example_document_analyzer_integration()
        
        # 파이프라인 사용법
        example_pipeline_usage()
        
        # 고급 검색
        example_advanced_search()
        
        print(f"\n🎉 모든 예제 실행 완료!")
        
    except Exception as e:
        print(f"❌ 예제 실행 실패: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()