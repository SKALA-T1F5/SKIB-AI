# Weaviate 로컬 서버에 연결하여 벡터 임베딩 및 메타데이터 업로드를 수행하는 코드
import os
from dotenv import load_dotenv
import weaviate
from weaviate.classes.config import Property, DataType

load_dotenv()

# 로컬 Weaviate 서버에 연결 (HTTP + gRPC 포트 지정)
_client = weaviate.connect_to_local(
    port=int(os.getenv("WEAVIATE_PORT", 8080)),
    grpc_port=int(os.getenv("WEAVIATE_GRPC_PORT", 50051)),
)


def get_client():
    return _client


def ensure_collection_exists(collection_name: str):
    if collection_name not in _client.collections.list_all():
        _client.collections.create(
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


def delete_collection(collection_name: str):
    if collection_name in _client.collections.list_all():
        _client.collections.delete(collection_name)
        print(f"✅ 컬렉션 삭제: {collection_name}")
    else:
        print(f"⚠️ 존재하지 않는 컬렉션: {collection_name}")


def upload_chunk_to_collection(chunk: dict, vector: list, collection_name: str):
    # # 컬렉션 존재 확인 및 필요시 생성
    ensure_collection_exists(collection_name)
    collection = _client.collections.get(collection_name)

    # 벡터와 함께 데이터 삽입 (UUID 자동 생성됨)
    collection.data.insert(
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
