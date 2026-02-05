"""Document Context Service - Session-aware wrapper for global document context."""

from typing import List, Dict, Optional
from pydantic import BaseModel
from app.services.vector_store import get_vector_store, VectorStore


class SearchResult(BaseModel):
    """Search result from document context."""
    text: str
    score: float
    filename: str
    file_id: str
    chunk_index: int
    folder_id: Optional[str] = None


class DocumentInfo(BaseModel):
    """Document metadata information."""
    file_id: str
    filename: str
    folder_id: Optional[str] = None
    chunk_count: int


class DocumentContext:
    """Session-aware document context wrapper.

    Provides a high-level interface to the vector store for document
    search and retrieval with session-based context tracking.
    """

    def __init__(self, session_id: str = "default"):
        self.session_id = session_id
        self._vector_store: Optional[VectorStore] = None

    @property
    def vector_store(self) -> VectorStore:
        """Lazy-load the vector store singleton."""
        if self._vector_store is None:
            self._vector_store = get_vector_store()
        return self._vector_store

    def search(self, query: str, n_results: int = 5) -> List[SearchResult]:
        """Search documents with metadata.

        Args:
            query: Search query string
            n_results: Maximum number of results to return

        Returns:
            List of SearchResult with text, score, and metadata
        """
        results = self.vector_store.search(query, n_results=n_results)

        search_results = []
        for result in results:
            metadata = result.get("metadata", {})
            search_results.append(SearchResult(
                text=result.get("text", ""),
                score=result.get("score", 0.0),
                filename=metadata.get("filename", "unknown"),
                file_id=metadata.get("file_id", ""),
                chunk_index=metadata.get("chunk_index", 0),
                folder_id=metadata.get("folder_id"),
            ))

        return search_results

    def get_all_documents(self) -> List[DocumentInfo]:
        """List all ingested documents from ChromaDB metadata.

        Returns:
            List of DocumentInfo with file metadata and chunk counts
        """
        # Get all items from the collection
        collection = self.vector_store.collection

        # Fetch all metadata (ChromaDB allows getting all with include)
        try:
            all_data = collection.get(include=["metadatas"])
        except Exception:
            return []

        if not all_data or not all_data.get("metadatas"):
            return []

        # Group by file_id to count chunks and get metadata
        documents: Dict[str, DocumentInfo] = {}

        for metadata in all_data["metadatas"]:
            if not metadata:
                continue

            file_id = metadata.get("file_id", "")
            if not file_id:
                continue

            if file_id not in documents:
                documents[file_id] = DocumentInfo(
                    file_id=file_id,
                    filename=metadata.get("filename", "unknown"),
                    folder_id=metadata.get("folder_id"),
                    chunk_count=0,
                )

            documents[file_id].chunk_count += 1

        return list(documents.values())

    def get_context_summary(self) -> str:
        """Get summary of active document context for prompts.

        Returns:
            Human-readable summary of available documents
        """
        documents = self.get_all_documents()

        if not documents:
            return "No documents have been ingested yet."

        doc_list = []
        total_chunks = 0

        for doc in documents:
            doc_list.append(f"- {doc.filename} ({doc.chunk_count} chunks)")
            total_chunks += doc.chunk_count

        summary = f"Document Context ({len(documents)} documents, {total_chunks} chunks):\n"
        summary += "\n".join(doc_list)

        return summary

    def get_document_chunks(self, file_id: str) -> List[str]:
        """Get all chunks for a specific document.

        Args:
            file_id: The file ID to retrieve chunks for

        Returns:
            List of chunk texts in order
        """
        collection = self.vector_store.collection

        try:
            # Query by file_id metadata
            results = collection.get(
                where={"file_id": file_id},
                include=["documents", "metadatas"]
            )
        except Exception:
            return []

        if not results or not results.get("documents"):
            return []

        # Sort by chunk_index
        chunks_with_index = []
        for doc, meta in zip(results["documents"], results["metadatas"]):
            chunk_index = meta.get("chunk_index", 0) if meta else 0
            chunks_with_index.append((chunk_index, doc))

        chunks_with_index.sort(key=lambda x: x[0])
        return [chunk for _, chunk in chunks_with_index]


# Singleton manager
_context_cache: Dict[str, DocumentContext] = {}


def get_document_context(session_id: str = "default") -> DocumentContext:
    """Get or create a DocumentContext for the given session.

    Args:
        session_id: Session identifier for context isolation

    Returns:
        DocumentContext instance for the session
    """
    if session_id not in _context_cache:
        _context_cache[session_id] = DocumentContext(session_id)
    return _context_cache[session_id]


def clear_document_context(session_id: str = "default") -> None:
    """Clear the document context cache for a session.

    Args:
        session_id: Session identifier to clear
    """
    if session_id in _context_cache:
        del _context_cache[session_id]


def clear_all_document_contexts() -> None:
    """Clear all document context caches."""
    _context_cache.clear()
