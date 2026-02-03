import chromadb
from chromadb.config import Settings
from openai import OpenAI
from pathlib import Path
from typing import List
import os


class VectorStore:
    """Vector store using ChromaDB with OpenAI embeddings."""
    
    def __init__(self, persist_dir: Path | None = None):
        if persist_dir is None:
            persist_dir = Path("./chroma_db")
        
        self.client = chromadb.PersistentClient(
            path=str(persist_dir),
            settings=Settings(anonymized_telemetry=False)
        )
        self.collection = self.client.get_or_create_collection(
            name="documents",
            metadata={"hnsw:space": "cosine"}
        )
        self.openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI."""
        response = self.openai.embeddings.create(
            model="text-embedding-3-small",
            input=texts
        )
        return [e.embedding for e in response.data]
    
    def add_documents(
        self, 
        chunks: List[str], 
        metadata: List[dict], 
        ids: List[str]
    ) -> None:
        """Add document chunks to the vector store."""
        if not chunks:
            return
        embeddings = self.embed(chunks)
        self.collection.add(
            documents=chunks,
            embeddings=embeddings,
            metadatas=metadata,
            ids=ids
        )
    
    def search(self, query: str, n_results: int = 5) -> List[dict]:
        """Search for similar documents."""
        query_embedding = self.embed([query])[0]
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"]
        )
        
        if not results["documents"] or not results["documents"][0]:
            return []
        
        return [
            {
                "text": doc,
                "metadata": meta,
                "score": 1 - dist  # Convert distance to similarity
            }
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0]
            )
        ]
    
    def clear(self) -> None:
        """Clear all documents from the collection."""
        self.client.delete_collection("documents")
        self.collection = self.client.get_or_create_collection(
            name="documents",
            metadata={"hnsw:space": "cosine"}
        )
