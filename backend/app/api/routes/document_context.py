"""Document Context API routes."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from app.services.document_context import (
    get_document_context,
    SearchResult,
    DocumentInfo,
)

router = APIRouter(prefix="/document-context", tags=["document-context"])


# Request/Response Models
class SearchRequest(BaseModel):
    query: str
    n_results: int = 5
    session_id: Optional[str] = "default"


class SearchResponse(BaseModel):
    results: List[SearchResult]
    query: str


class DocumentsResponse(BaseModel):
    documents: List[DocumentInfo]
    total_count: int


class SummaryResponse(BaseModel):
    summary: str
    document_count: int
    session_id: str


# ============== Endpoints ============== #

@router.get("/documents", response_model=DocumentsResponse)
async def list_documents(session_id: str = "default"):
    """List all ingested documents.

    Returns metadata about all documents in the vector store
    including filename, file_id, and chunk count.
    """
    try:
        context = get_document_context(session_id)
        documents = context.get_all_documents()

        return DocumentsResponse(
            documents=documents,
            total_count=len(documents)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")


@router.post("/search", response_model=SearchResponse)
async def search_documents(req: SearchRequest):
    """Search documents with semantic query.

    Performs vector similarity search across all ingested documents
    and returns relevant chunks with metadata.
    """
    if not req.query or not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        context = get_document_context(req.session_id or "default")
        results = context.search(req.query, n_results=req.n_results)

        return SearchResponse(
            results=results,
            query=req.query
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/summary", response_model=SummaryResponse)
async def get_context_summary(session_id: str = "default"):
    """Get summary of current document context.

    Returns a human-readable summary of the available documents
    suitable for including in AI prompts.
    """
    try:
        context = get_document_context(session_id)
        summary = context.get_context_summary()
        documents = context.get_all_documents()

        return SummaryResponse(
            summary=summary,
            document_count=len(documents),
            session_id=session_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get summary: {str(e)}")


@router.get("/documents/{file_id}/chunks")
async def get_document_chunks(file_id: str, session_id: str = "default"):
    """Get all chunks for a specific document.

    Returns the full content of a document as a list of chunks
    in their original order.
    """
    try:
        context = get_document_context(session_id)
        chunks = context.get_document_chunks(file_id)

        if not chunks:
            raise HTTPException(status_code=404, detail="Document not found or has no chunks")

        return {
            "file_id": file_id,
            "chunks": chunks,
            "chunk_count": len(chunks)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get document chunks: {str(e)}")
