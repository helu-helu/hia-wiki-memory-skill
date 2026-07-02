from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple

class BaseVectorStore(ABC):
    @abstractmethod
    def upsert_batch(self, ids: List[str], documents: List[str], metadatas: List[Dict[str, Any]]) -> None:
        """Upsert a batch of documents and their metadatas."""
        pass
        
    @abstractmethod
    def delete_batch(self, ids: List[str]) -> None:
        """Delete a batch of documents by ID."""
        pass
        
    @abstractmethod
    def search(self, query: str, n_results: int, where: Dict[str, Any] = None) -> Tuple[List[str], List[float], List[Dict[str, Any]]]:
        """Returns a tuple of (documents, distances, metadatas)."""
        pass
        
    @abstractmethod
    def get_all_ids(self) -> List[str]:
        """Returns all document IDs currently in the vector store."""
        pass
