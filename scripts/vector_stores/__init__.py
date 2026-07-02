import os
from dotenv import load_dotenv
load_dotenv()

from .base import BaseVectorStore

def get_vector_store(wiki_dir: str) -> BaseVectorStore:
    store_type = os.environ.get("VECTOR_STORE", "chroma").lower()
    
    if store_type == "pinecone":
        from .pinecone_store import PineconeStore
        return PineconeStore(wiki_dir)
    else:
        from .chroma_store import ChromaStore
        return ChromaStore(wiki_dir)
