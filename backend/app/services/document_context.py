"""Document context service wrapping VectorStore with session-aware caching."""

from typing import List, Optional
from pydantic import BaseModel

from app.services.vector_store import get_vector_store


class SearchResult(BaseModel):
    """Search result from document context."""
    text: str
    filename: str
    file_id: str
    score: float
    chunk_index: int


class DocumentInfo(BaseModel):
    """Document information."""
    file_id: str
    filename: str
    chunk_count: int


class DocumentContext:
    """Wraps VectorStore for document agent tool access."""

    def __init__(self):
        self._store = get_vector_store()

    def search(self, query: str, n_results: int = 5) -> List[SearchResult]:
        """Search vector store for relevant document chunks."""
        results = self._store.search(query, n_results=n_results)
        return [
            SearchResult(
                text=r["text"],
                filename=r["metadata"].get("filename", "unknown"),
                file_id=r["metadata"].get("file_id", "unknown"),
                score=r["score"],
                chunk_index=r["metadata"].get("chunk_index", 0)
            )
            for r in results
        ]

    def get_all_documents(self) -> List[DocumentInfo]:
        """List unique documents in the vector store by file_id/filename."""
        collection = self._store.collection
        result = collection.get(include=["metadatas"])

        if not result["metadatas"]:
            return []

        seen = {}
        for meta in result["metadatas"]:
            file_id = meta.get("file_id", meta.get("filename", "unknown"))
            if file_id not in seen:
                seen[file_id] = {
                    "file_id": file_id,
                    "filename": meta.get("filename", file_id),
                    "chunk_count": 0
                }
            seen[file_id]["chunk_count"] += 1
        
        return [DocumentInfo(**doc) for doc in seen.values()]

    def get_context_summary(self) -> str:
        """Get a summary of available documents."""
        docs = self.get_all_documents()
        if not docs:
            return "No documents available."
        lines = [f"- {d.filename} ({d.chunk_count} chunks)" for d in docs]
        return f"Available documents ({len(docs)}):\n" + "\n".join(lines)

    def get_document_chunks(self, file_id: str) -> List[str]:
        """Get all chunks for a specific file as text strings, sorted by chunk_index."""
        collection = self._store.collection
        result = collection.get(
            where={"file_id": file_id},
            include=["documents", "metadatas"],
        )

        if not result["documents"]:
            return []

        chunks = []
        for doc, meta in zip(result["documents"], result["metadatas"]):
            chunks.append({
                "text": doc,
                "chunk_index": meta.get("chunk_index", 0),
            })

        chunks.sort(key=lambda c: c["chunk_index"])
        return [chunk["text"] for chunk in chunks]


# Singleton
_instance: Optional[DocumentContext] = None


def get_document_context(session_id: str = "default") -> DocumentContext:
    """Get singleton DocumentContext instance."""
    global _instance
    if _instance is None:
        _instance = DocumentContext()
    return _instance
