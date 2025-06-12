#!/usr/bin/env python3
"""
VectorDB(Weaviate) 저장 내용 확인 스크립트
파싱된 내용들이 vectorDB에 잘 저장되었는지 검증

사용법:
python check_vectordb.py [collection_name]
"""

import sys
import json
from db.vectorDB.weaviate_utils import get_client


def list_all_collections():
    """모든 컬렉션 목록 조회"""
    client = get_client()
    collections = client.collections.list_all()
    
    print("📊 Weaviate 컬렉션 목록:")
    print("=" * 50)
    
    if not collections:
        print("❌ 저장된 컬렉션이 없습니다.")
        return []
    
    collection_info = []
    for collection_name in collections:
        try:
            collection = client.collections.get(collection_name)
            # 컬렉션의 객체 수 조회
            count_result = collection.aggregate.over_all(total_count=True)
            count = count_result.total_count if count_result.total_count else 0
            
            collection_info.append({
                "name": collection_name,
                "count": count
            })
            
            print(f"🔹 {collection_name}: {count}개 객체")
            
        except Exception as e:
            print(f"⚠️ {collection_name}: 조회 실패 ({e})")
    
    return collection_info


def check_collection_details(collection_name: str, limit: int = 5):
    """특정 컬렉션의 상세 내용 확인"""
    client = get_client()
    
    print(f"\n📋 컬렉션 '{collection_name}' 상세 조회")
    print("=" * 60)
    
    try:
        collection = client.collections.get(collection_name)
        
        # 전체 개수 조회
        count_result = collection.aggregate.over_all(total_count=True)
        total_count = count_result.total_count if count_result.total_count else 0
        
        print(f"총 객체 수: {total_count}개")
        
        if total_count == 0:
            print("❌ 저장된 데이터가 없습니다.")
            return
        
        # 샘플 데이터 조회
        print(f"\n📄 샘플 데이터 (최대 {limit}개):")
        print("-" * 50)
        
        response = collection.query.fetch_objects(limit=limit)
        
        for i, obj in enumerate(response.objects, 1):
            props = obj.properties
            print(f"\n[{i}] {props.get('chunk_id', 'N/A')}")
            print(f"   타입: {props.get('chunk_type', 'N/A')}")
            print(f"   프로젝트: {props.get('project', 'N/A')}")
            print(f"   소스: {props.get('source', 'N/A')}")
            print(f"   섹션: {props.get('section_title', 'N/A')}")
            
            # 텍스트 내용 (처음 100자만)
            source_text = props.get('source_text', '')
            if source_text:
                preview = source_text[:100] + "..." if len(source_text) > 100 else source_text
                print(f"   내용: {preview}")
            
            # 벡터 존재 여부
            vector_exists = obj.vector is not None
            print(f"   벡터: {'✅ 있음' if vector_exists else '❌ 없음'}")
        
        # 프로젝트별 통계
        print(f"\n📊 프로젝트별 통계:")
        print("-" * 30)
        
        # 모든 객체를 가져와서 프로젝트별로 집계
        all_response = collection.query.fetch_objects(limit=1000)  # 최대 1000개까지
        project_stats = {}
        
        for obj in all_response.objects:
            project = obj.properties.get('project', 'Unknown')
            if project in project_stats:
                project_stats[project] += 1
            else:
                project_stats[project] = 1
        
        for project, count in project_stats.items():
            print(f"   {project}: {count}개")
    
    except Exception as e:
        print(f"❌ 컬렉션 조회 실패: {e}")


def search_collection(collection_name: str, query: str, limit: int = 3):
    """컬렉션에서 텍스트 검색"""
    client = get_client()
    
    print(f"\n🔍 컬렉션 '{collection_name}'에서 '{query}' 검색")
    print("=" * 60)
    
    try:
        collection = client.collections.get(collection_name)
        
        # BM25 키워드 검색
        response = collection.query.bm25(
            query=query,
            limit=limit,
            return_metadata=['score']
        )
        
        if not response.objects:
            print("❌ 검색 결과가 없습니다.")
            return
        
        for i, obj in enumerate(response.objects, 1):
            props = obj.properties
            score = obj.metadata.score if obj.metadata else 0
            
            print(f"\n[{i}] 점수: {score:.3f}")
            print(f"   ID: {props.get('chunk_id', 'N/A')}")
            print(f"   프로젝트: {props.get('project', 'N/A')}")
            print(f"   소스: {props.get('source', 'N/A')}")
            
            # 매칭된 텍스트 미리보기
            source_text = props.get('source_text', '')
            if source_text:
                preview = source_text[:150] + "..." if len(source_text) > 150 else source_text
                print(f"   내용: {preview}")
    
    except Exception as e:
        print(f"❌ 검색 실패: {e}")


def get_collection_schema(collection_name: str):
    """컬렉션 스키마 정보 조회"""
    client = get_client()
    
    print(f"\n🏗️ 컬렉션 '{collection_name}' 스키마")
    print("=" * 50)
    
    try:
        collection = client.collections.get(collection_name)
        config = collection.config.get()
        
        print(f"컬렉션명: {config.name}")
        print(f"벡터화 설정: {config.vectorizer_config}")
        
        print("\n속성 목록:")
        for prop in config.properties:
            print(f"   - {prop.name} ({prop.data_type})")
    
    except Exception as e:
        print(f"❌ 스키마 조회 실패: {e}")


def main():
    """메인 함수"""
    print("🔍 VectorDB(Weaviate) 저장 내용 확인")
    print("=" * 50)
    
    try:
        # 1. 모든 컬렉션 목록 표시
        collections = list_all_collections()
        
        if not collections:
            print("\n💡 vectorDB에 저장된 데이터가 없습니다.")
            print("   통합 파서를 실행하여 데이터를 저장해보세요:")
            print("   python -m agents.question_generator.run_pipeline 'file.pdf'")
            return
        
        # 2. 특정 컬렉션 확인 (인자로 제공된 경우)
        if len(sys.argv) > 1:
            collection_name = sys.argv[1]
            
            if collection_name in [c["name"] for c in collections]:
                check_collection_details(collection_name)
                get_collection_schema(collection_name)
                
                # 샘플 검색 수행
                print(f"\n🔍 샘플 검색 테스트")
                search_collection(collection_name, "계약", 2)
                search_collection(collection_name, "자동차", 2)
            else:
                print(f"❌ 컬렉션 '{collection_name}'을 찾을 수 없습니다.")
                print(f"사용 가능한 컬렉션: {[c['name'] for c in collections]}")
        
        # 3. 가장 큰 컬렉션 자동 확인
        else:
            if collections:
                # 가장 많은 데이터를 가진 컬렉션 선택
                largest_collection = max(collections, key=lambda x: x["count"])
                
                if largest_collection["count"] > 0:
                    print(f"\n📍 가장 큰 컬렉션 '{largest_collection['name']}' 자동 확인:")
                    check_collection_details(largest_collection["name"], 3)
                    
                    # 간단한 검색 테스트
                    search_collection(largest_collection["name"], "프로세스", 2)
    
    except Exception as e:
        print(f"❌ VectorDB 연결 실패: {e}")
        print("💡 Weaviate 서버가 실행 중인지 확인해주세요.")
        print("   docker-compose up -d 또는 해당 서비스 시작 명령을 실행해보세요.")


if __name__ == "__main__":
    main()