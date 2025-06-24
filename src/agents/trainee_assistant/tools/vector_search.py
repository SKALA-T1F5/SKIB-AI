from typing import List, Dict
import asyncio
import chromadb
from chromadb.utils import embedding_functions
from src.agents.trainee_assistant.models import SearchResult
from .base import BaseTool, normalize_collection_name

class VectorSearchTool(BaseTool):
    def __init__(self, document_name: str, db_path: str = "./chroma_db"):
        normalized_name = normalize_collection_name(document_name)
        self.client = chromadb.PersistentClient(path=db_path)
        self.embedding_function = embedding_functions.DefaultEmbeddingFunction()

        try:
            self.collection = self.client.get_collection(
                name=normalized_name,
                embedding_function=self.embedding_function
            )
        except Exception as e:
            raise ValueError(f"❌ ChromaDB 컬렉션 '{normalized_name}' 을 찾을 수 없습니다: {e}")

    async def search(self, query: str, n_results: int = 5, **kwargs) -> List[SearchResult]:
        try:
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                lambda: self.collection.query(
                    query_texts=[query],
                    n_results=n_results,
                    include=['documents', 'metadatas', 'distances']
                )
            )

            search_results = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    search_results.append(SearchResult(
                        content=doc,
                        source="vector_db",
                        score=1.0 - results['distances'][0][i],
                        metadata=results['metadatas'][0][i] if results['metadatas'] else {}
                    ))

            return search_results
        except Exception as e:
            print(f"Vector search error: {e}")
            return []

    def add_documents(self, documents: List[str], metadatas: List[Dict] = None, ids: List[str] = None):
        if not ids:
            ids = [f"doc_{i}" for i in range(len(documents))]
        self.collection.add(
            documents=documents,
            metadatas=metadatas or [{}] * len(documents),
            ids=ids
        )