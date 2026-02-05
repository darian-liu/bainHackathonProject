"""Document context service wrapping VectorStore with session-aware caching."""

from typing import List, Optional

from app.services.vector_store import get_vector_store


class DocumentContext:
    """Wraps VectorStore for document agent tool access."""

    def __init__(self):
        self._store = get_vector_store()

    def get_relevant_context(self, query: str, n_results: int = 5) -> List[dict]:
        """Search vector store for relevant document chunks."""
        return self._store.search(query, n_results=n_results)

    def get_all_documents(self) -> List[dict]:
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
                    "source": meta.get("source", ""),
                }
        return list(seen.values())

    def get_document_chunks(self, file_id: str) -> List[dict]:
        """Get all chunks for a specific file, sorted by chunk_index."""
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
                "metadata": meta,
            })

        chunks.sort(key=lambda c: c["chunk_index"])
        return chunks


# Singleton
_instance: Optional[DocumentContext] = None


def get_document_context() -> DocumentContext:
    """Get singleton DocumentContext instance."""
    global _instance
    if _instance is None:
        _instance = DocumentContext()
    return _instance
