from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import List, Optional

from app.services.document_source import get_document_source
from app.services.vector_store import get_vector_store
from app.services.ingestion_service import ingest_documents
from app.agents.camel_agent import CamelRAGAgent
from app.agents.simple_agent import SimpleChatAgent
from app.services.event_bus import event_bus
from app.core.config import settings

# Import limiter from main app
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/data-room", tags=["data-room"])


class IngestRequest(BaseModel):
    folder_id: str


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    sources: List[dict]


# TODO: [SECURITY] Add authentication middleware before production deployment
# See: https://fastapi.tiangolo.com/tutorial/security/
@router.get("/folders")
async def list_folders(parent_id: Optional[str] = None):
    """List folders from document source."""
    source = get_document_source()
    folders = await source.list_folders(parent_id)
    return {"folders": [f.model_dump() for f in folders]}


# TODO: [SECURITY] Add authentication middleware before production deployment
# See: https://fastapi.tiangolo.com/tutorial/security/
@router.get("/folders/{folder_id}/files")
async def list_files(folder_id: str):
    """List files in a folder."""
    source = get_document_source()
    files = await source.list_files(folder_id)
    return {"files": [f.model_dump() for f in files]}


# TODO: [SECURITY] Add authentication middleware before production deployment
# See: https://fastapi.tiangolo.com/tutorial/security/
@router.post("/ingest")
@limiter.limit("10/minute")
async def ingest_folder(request: Request, body: IngestRequest):
    """Ingest all documents from a folder into the vector store."""
    source = get_document_source()
    results = await ingest_documents(source, body.folder_id)

    return {
        "results": [
            {
                "file": r.file,
                "status": r.status,
                "chunks": r.chunks,
                "reason": r.reason,
                "error": r.error,
            }
            for r in results
        ]
    }


# TODO: [SECURITY] Add authentication middleware before production deployment
# See: https://fastapi.tiangolo.com/tutorial/security/
@router.post("/chat", response_model=ChatResponse)
@limiter.limit("20/minute")
async def chat(request: Request, body: ChatRequest):
    """Chat with the ingested documents using RAG."""
    vector_store = get_vector_store()

    # Use CAMEL agent by default, fall back to simple agent if configured
    use_simple = settings.use_simple_agent
    agent = SimpleChatAgent() if use_simple else CamelRAGAgent()

    # Search for relevant context
    search_results = vector_store.search(body.message, n_results=5)

    if not search_results:
        return ChatResponse(
            response="I don't have any documents to search. Please ingest some documents first.",
            sources=[],
        )

    context = [r["text"] for r in search_results]
    sources = [r["metadata"] for r in search_results]

    # Collect response
    response_chunks = []

    async def emit_event(event):
        await event_bus.broadcast(event.model_dump())

    async for chunk in agent.chat(body.message, context, emit_event):
        response_chunks.append(chunk)

    return ChatResponse(response="".join(response_chunks), sources=sources)


# TODO: [SECURITY] Add authentication middleware before production deployment
# See: https://fastapi.tiangolo.com/tutorial/security/
@router.delete("/documents")
async def clear_documents():
    """Clear all ingested documents."""
    vector_store = get_vector_store()
    vector_store.clear()
    return {"status": "cleared"}
