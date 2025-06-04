"""
Weaviate 벡터 데이터베이스와 연결하여 다음의 기능 제공
컬렉션 존재 여부 확인 및 생성 (ensure_collection_exists)
벡터 및 메타데이터 업로드 (upload_chunk_to_collection)

업로드 시에는 chunk_id를 기반으로 UUID5를 생성해 중복을 방지하며 텍스트 기반 필드들과 함께 벡터를 저장합니다.
"""

import os
from dotenv import load_dotenv
from uuid import uuid5, NAMESPACE_URL

from weaviate import WeaviateClient
from weaviate.connect import ConnectionParams
from weaviate.connect.http import HttpConfig
from weaviate.connect.grpc import GrpcConfig
from weaviate.collections import Property, DataType

load_dotenv()  # .env 파일에서 환경변수 불러오기 (WEAVIATE_URL 사용)

# Weaviate 클라이언트 설정 (HTTP + gRPC 연결)
client = WeaviateClient(
    connection_params=ConnectionParams.from_params(
        http=HttpConfig(host=os.getenv("WEAVIATE_URL", "http://localhost:8080")),
        grpc=GrpcConfig(port=50051),
    )
)


def ensure_collection_exists(collection_name: str):
    # 현재 존재하는 컬렉션 목록 확인
    if collection_name not in client.collections.list_all():
        # 컬렉션 생성: 속성(schema) 정의 포함
        client.collections.create(
            name=collection_name,
            properties=[
                Property(name="chunk_id", data_type=DataType.TEXT),
                Property(name="chunk_type", data_type=DataType.TEXT),
                Property(name="section_title", data_type=DataType.TEXT),
                Property(name="source_text", data_type=DataType.TEXT),
                Property(name="project", data_type=DataType.TEXT),
                Property(name="source", data_type=DataType.TEXT),
            ],
            vectorizer_config=None,
        )
        print(f"✅ 컬렉션 생성: {collection_name}")
    else:
        print(f"ℹ️ 이미 존재하는 컬렉션: {collection_name}")


def upload_chunk_to_collection(chunk: dict, vector: list, collection_name: str):
    # 1. 컬렉션 존재 여부 확인 및 필요시 생성
    ensure_collection_exists(collection_name)

    # 2. 업로드할 컬렉션 객체 가져오기
    collection = client.collections.get(collection_name)

    # 3. UUID5를 통해 고유 ID 생성 (chunk_id 기반)
    uuid = str(uuid5(NAMESPACE_URL, chunk["chunk_id"]))

    # 4. 데이터 삽입: 벡터 + 메타데이터 포함
    collection.data.insert(
        uuid=uuid,
        properties={
            "chunk_id": chunk["chunk_id"],
            "chunk_type": chunk["chunk_type"],
            "section_title": chunk.get("section_title", ""),
            "source_text": chunk["source_text"],
            "project": chunk["project"],
            "source": chunk["source"],
        },
        vector=vector,
    )
    print(f"✅ 업로드 완료: {chunk['chunk_id']} → 컬렉션 '{collection_name}'")
