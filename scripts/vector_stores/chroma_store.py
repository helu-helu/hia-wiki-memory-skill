import os
from typing import List, Dict, Any, Tuple
from .base import BaseVectorStore

try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    chromadb = None

class ChromaStore(BaseVectorStore):
    def __init__(self, wiki_dir: str):
        if chromadb is None:
            raise ImportError("chromadb is not installed. Please pip install chromadb.")
            
        db_path = os.path.join(wiki_dir, ".chroma_db")
        os.makedirs(db_path, exist_ok=True)
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(
            name="wiki_chunks",
            metadata={"hnsw:space": "cosine"}
        )

    def upsert_batch(self, ids: List[str], documents: List[str], metadatas: List[Dict[str, Any]]) -> None:
        if not ids: return
        self.collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )

    def delete_batch(self, ids: List[str]) -> None:
        if not ids: return
        self.collection.delete(ids=ids)

    def search(self, query: str, n_results: int, where: Dict[str, Any] = None) -> Tuple[List[str], List[float], List[Dict[str, Any]]]:
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where
        )
        
        docs = results['documents'][0] if results['documents'] else []
        distances = results['distances'][0] if results['distances'] else []
        metadatas = results['metadatas'][0] if results['metadatas'] else []
        
        return docs, distances, metadatas

    def get_all_ids(self) -> List[str]:
        existing_ids = []
        offset = 0
        limit = 5000
        while True:
            batch = self.collection.get(limit=limit, offset=offset)
            if not batch or not batch.get('ids'):
                break
            existing_ids.extend(batch['ids'])
            offset += limit
        return existing_ids
