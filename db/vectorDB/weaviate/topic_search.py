"""
JSON 파일의 main_topics 키워드를 기반으로 VectorDB에서 관련 문서를 검색하는 모듈
"""

import json
import os
from typing import Any, Dict, List

from sentence_transformers import SentenceTransformer

from .weaviate_utils import get_client


class TopicSearcher:
    def __init__(self, embedding_model_name: str = "BAAI/bge-base-en"):
        """
        TopicSearcher 초기화

        Args:
            embedding_model_name: 임베딩에 사용할 모델명
        """
        self.client = get_client()
        self.embedding_model = SentenceTransformer(embedding_model_name)

    def extract_main_topics_from_json(self, json_file_path: str) -> List[str]:
        """
        JSON 파일에서 main_topics 추출

        Args:
            json_file_path: JSON 파일 경로

        Returns:
            main_topics 리스트
        """
        try:
            with open(json_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            main_topics = data.get("content_analysis", {}).get("main_topics", [])
            print(f"📊 추출된 주요 토픽: {len(main_topics)}개")
            for i, topic in enumerate(main_topics, 1):
                print(f"  {i}. {topic}")

            return main_topics

        except Exception as e:
            print(f"❌ JSON 파일 읽기 오류: {e}")
            return []

    def search_by_keyword(
        self, keyword: str, collection_name: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        키워드로 VectorDB에서 유사한 문서 검색

        Args:
            keyword: 검색할 키워드
            collection_name: 검색할 컬렉션명
            limit: 반환할 결과 개수

        Returns:
            검색 결과 리스트
        """
        try:
            # 키워드를 벡터로 변환
            query_vector = self.embedding_model.encode(keyword).tolist()

            # Weaviate에서 벡터 검색 수행
            collection = self.client.collections.get(collection_name)

            response = collection.query.near_vector(
                near_vector=query_vector, limit=limit, return_metadata=["score"]
            )

            results = []
            for obj in response.objects:
                result = {
                    "uuid": str(obj.uuid),
                    "score": obj.metadata.score if obj.metadata else 0.0,
                    "properties": obj.properties,
                    "keyword": keyword,
                }
                results.append(result)

            return results

        except Exception as e:
            print(f"❌ 키워드 '{keyword}' 검색 오류: {e}")
            return []

    def search_multiple_topics(
        self, topics: List[str], collection_name: str, limit_per_topic: int = 3
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        여러 토픽에 대해 VectorDB 검색 수행

        Args:
            topics: 검색할 토픽 리스트
            collection_name: 검색할 컬렉션명
            limit_per_topic: 토픽당 반환할 결과 개수

        Returns:
            토픽별 검색 결과 딕셔너리
        """
        all_results = {}

        print(f"\n🔍 VectorDB 검색 시작 (컬렉션: {collection_name})")
        print(f"📝 검색할 토픽: {len(topics)}개")

        for i, topic in enumerate(topics, 1):
            print(f"\n[{i}/{len(topics)}] 검색 중: '{topic}'")

            results = self.search_by_keyword(topic, collection_name, limit_per_topic)
            all_results[topic] = results

            if results:
                print(f"  ✅ 찾은 결과: {len(results)}개")
                for j, result in enumerate(results, 1):
                    score = result.get("score", 0.0)
                    chunk_id = result.get("properties", {}).get("chunk_id", "N/A")
                    print(f"    {j}. 점수: {score:.3f}, ID: {chunk_id}")
            else:
                print(f"  ❌ 검색 결과 없음")

        return all_results

    def get_available_collections(self) -> List[str]:
        """
        사용 가능한 컬렉션 목록 반환

        Returns:
            컬렉션명 리스트
        """
        try:
            collections = list(self.client.collections.list_all().keys())
            print(f"📚 사용 가능한 컬렉션: {collections}")
            return collections
        except Exception as e:
            print(f"❌ 컬렉션 목록 조회 오류: {e}")
            return []


def search_topics_from_json(
    json_file_path: str, collection_name: str = None, limit_per_topic: int = 3
) -> Dict[str, Any]:
    """
    JSON 파일의 main_topics를 기반으로 VectorDB에서 관련 문서 검색

    Args:
        json_file_path: JSON 파일 경로
        collection_name: 검색할 컬렉션명 (None이면 자동 추정)
        limit_per_topic: 토픽당 반환할 결과 개수

    Returns:
        검색 결과와 메타데이터를 포함한 딕셔너리
    """
    searcher = TopicSearcher()

    # 1. JSON에서 main_topics 추출
    topics = searcher.extract_main_topics_from_json(json_file_path)

    if not topics:
        return {"error": "main_topics를 찾을 수 없습니다", "json_file": json_file_path}

    # 2. 컬렉션명 자동 추정 (파일명 기반)
    if collection_name is None:
        from utils.change_name import normalize_collection_name

        filename = os.path.splitext(os.path.basename(json_file_path))[0]
        # "_complete_test" 같은 접미사 제거
        filename = filename.replace("_complete_test", "").replace(
            "_keywords_summary", ""
        )
        collection_name = normalize_collection_name(filename)
        print(f"🎯 자동 추정된 컬렉션명: {collection_name}")

    # 3. 사용 가능한 컬렉션 확인
    available_collections = searcher.get_available_collections()
    if collection_name not in available_collections:
        return {
            "error": f'컬렉션 "{collection_name}"을 찾을 수 없습니다',
            "available_collections": available_collections,
            "json_file": json_file_path,
        }

    # 4. 토픽별 검색 수행
    search_results = searcher.search_multiple_topics(
        topics, collection_name, limit_per_topic
    )

    # 5. 결과 요약
    total_results = sum(len(results) for results in search_results.values())
    successful_topics = [topic for topic, results in search_results.items() if results]

    result_summary = {
        "json_file": json_file_path,
        "collection_name": collection_name,
        "topics_searched": len(topics),
        "topics_with_results": len(successful_topics),
        "total_results_found": total_results,
        "search_results": search_results,
        "summary": {
            "successful_topics": successful_topics,
            "empty_topics": [
                topic for topic, results in search_results.items() if not results
            ],
        },
    }

    print(f"\n📊 검색 완료!")
    print(f"  - 검색된 토픽: {len(topics)}개")
    print(f"  - 결과가 있는 토픽: {len(successful_topics)}개")
    print(f"  - 총 검색 결과: {total_results}개")

    return result_summary


# 사용 예시 및 테스트
if __name__ == "__main__":
    # 테스트용 JSON 파일 경로 설정
    test_json_path = "data/outputs/자동차 리포트_complete_test.json"

    if os.path.exists(test_json_path):
        print("🚀 테스트 시작")
        results = search_topics_from_json(test_json_path)

        # 결과를 JSON 파일로 저장
        output_path = "data/search_outputs/topic_search_results.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"💾 검색 결과 저장: {output_path}")
    else:
        print(f"❌ 테스트 파일을 찾을 수 없습니다: {test_json_path}")
