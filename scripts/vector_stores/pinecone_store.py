import os
from typing import List, Dict, Any, Tuple
from .base import BaseVectorStore

try:
    from pinecone import Pinecone
    import openai
except ImportError:
    Pinecone = None
    openai = None

class PineconeStore(BaseVectorStore):
    def __init__(self, wiki_dir: str):
        if Pinecone is None or openai is None:
            raise ImportError("pinecone-client and openai must be installed to use PineconeStore.")
            
        api_key = os.environ.get("PINECONE_API_KEY")
        environment = os.environ.get("PINECONE_ENV", "us-east-1")
        index_name = os.environ.get("PINECONE_INDEX_NAME", "wiki-memory")
        
        if not api_key:
            raise ValueError("PINECONE_API_KEY environment variable is required.")
            
        self.pc = Pinecone(api_key=api_key)
        self.index = self.pc.Index(index_name)
        
        self.openai_client = openai.Client()

    def _get_embeddings(self, texts: List[str]) -> List[List[float]]:
        response = self.openai_client.embeddings.create(
            input=texts,
            model="text-embedding-3-small"
        )
        return [data.embedding for data in response.data]

    def upsert_batch(self, ids: List[str], documents: List[str], metadatas: List[Dict[str, Any]]) -> None:
        if not ids: return
        
        embeddings = self._get_embeddings(documents)
        
        vectors = []
        for i in range(len(ids)):
            meta = metadatas[i].copy()
            meta["text"] = documents[i] # Store the original text in metadata
            vectors.append({
                "id": ids[i],
                "values": embeddings[i],
                "metadata": meta
            })
            
        self.index.upsert(vectors=vectors)

    def delete_batch(self, ids: List[str]) -> None:
        if not ids: return
        self.index.delete(ids=ids)

    def search(self, query: str, n_results: int, where: Dict[str, Any] = None) -> Tuple[List[str], List[float], List[Dict[str, Any]]]:
        query_embedding = self._get_embeddings([query])[0]
        
        # Convert chroma where syntax to pinecone where syntax
        # Basic mapping, might need more complex translation depending on usage
        filter_dict = where if where else None
            
        results = self.index.query(
            vector=query_embedding,
            top_k=n_results,
            filter=filter_dict,
            include_metadata=True
        )
        
        docs = []
        distances = []
        metadatas = []
        
        for match in results.matches:
            # Pinecone score is similarity (higher is better for cosine), Chroma distance is lower is better
            # Return raw score as distance, callers might need to handle the difference
            distances.append(match.score)
            
            meta = match.metadata or {}
            text = meta.pop("text", "")
            
            docs.append(text)
            metadatas.append(meta)
            
        return docs, distances, metadatas

    def get_all_ids(self) -> List[str]:
        # Pinecone doesn't natively support getting ALL IDs easily.
        # Often this is done via list_paginated or exporting.
        # For small-medium wikis, we could use list endpoint if available.
        # As of recent pinecone-client, list functionality exists for serverless.
        ids = []
        try:
            for ids_batch in self.index.list():
                ids.extend(ids_batch)
        except Exception:
            pass # Fallback or warning if not supported
        return ids
