import chromadb
from chromadb.config import Settings as ChromaSettings
from openai import OpenAI
from pathlib import Path
from typing import List, Optional

from app.core.config import settings

# Singleton instance
_vector_store_instance: Optional["VectorStore"] = None


class VectorStore:
    """Vector store using ChromaDB with OpenAI embeddings."""

    def __init__(self, persist_dir: Path | None = None):
        if persist_dir is None:
            persist_dir = Path("./chroma_db")

        self.client = chromadb.PersistentClient(
            path=str(persist_dir), settings=ChromaSettings(anonymized_telemetry=False)
        )
        self.collection = self.client.get_or_create_collection(
            name="documents", metadata={"hnsw:space": "cosine"}
        )
        
        # Configure OpenAI client with optional Portkey base URL
        client_config = {"api_key": settings.openai_api_key}
        if settings.openai_base_url:
            client_config["base_url"] = settings.openai_base_url
        self.openai = OpenAI(**client_config)

        # Detect Portkey prefix from model name (e.g. "@personal-openai/gpt-4o" -> "@personal-openai/")
        model_name = settings.openai_model or ""
        if "/" in model_name:
            self._model_prefix = model_name.rsplit("/", 1)[0] + "/"
        else:
            self._model_prefix = ""

    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI."""
        model = f"{self._model_prefix}text-embedding-3-small"
        response = self.openai.embeddings.create(
            model=model, input=texts
        )
        return [e.embedding for e in response.data]

    def add_documents(
        self, chunks: List[str], metadata: List[dict], ids: List[str]
    ) -> None:
        """Add document chunks to the vector store."""
        if not chunks:
            return
        embeddings = self.embed(chunks)
        self.collection.add(
            documents=chunks, embeddings=embeddings, metadatas=metadata, ids=ids
        )

    def search(self, query: str, n_results: int = 5) -> List[dict]:
        """Search for similar documents."""
        query_embedding = self.embed([query])[0]
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )

        if not results["documents"] or not results["documents"][0]:
            return []

        return [
            {
                "text": doc,
                "metadata": meta,
                "score": 1 - dist,  # Convert distance to similarity
            }
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            )
        ]

    def clear(self) -> None:
        """Clear all documents from the collection."""
        self.client.delete_collection("documents")
        self.collection = self.client.get_or_create_collection(
            name="documents", metadata={"hnsw:space": "cosine"}
        )


def get_vector_store() -> VectorStore:
    """Get the singleton VectorStore instance."""
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = VectorStore()
    return _vector_store_instance


def reset_vector_store() -> None:
    """Reset the singleton instance (useful for testing)."""
    global _vector_store_instance
    _vector_store_instance = None
