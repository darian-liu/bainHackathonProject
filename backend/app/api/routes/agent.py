"""Agent HTTP routes for document agent chat, upload, and download."""

import logging
import mimetypes
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.agents.document_agent import DocumentAgent, AGENT_OUTPUTS_DIR
from app.services.document_parser import DocumentParser
from app.services.vector_store import get_vector_store
from app.services.event_bus import event_bus
from app.core.events import AgentEvent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["agent"])

# In-memory session store for conversation history
_sessions: dict[str, list] = {}


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    project_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    session_id: str
    tool_calls: list


# ── Chat ──────────────────────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
async def agent_chat(body: ChatRequest):
    """Chat with the document agent. Supports tool calling and expert queries."""
    session_id = body.session_id or str(uuid.uuid4())

    # Get or create conversation history for this session
    if session_id not in _sessions:
        _sessions[session_id] = []
    history = _sessions[session_id]

    async def emit_event(event: AgentEvent):
        await event_bus.broadcast(event.model_dump())

    agent = DocumentAgent()
    result = await agent.chat(
        message=body.message,
        conversation_history=history,
        on_event=emit_event,
        project_id=body.project_id,
    )

    # Append to session history for multi-turn conversations
    history.append({"role": "user", "content": body.message})
    history.append({"role": "assistant", "content": result["response"]})

    return ChatResponse(
        response=result["response"],
        session_id=session_id,
        tool_calls=result["tool_calls"],
    )


# ── Upload ────────────────────────────────────────────────────────────

SUPPORTED_UPLOAD_EXTENSIONS = {".pdf", ".docx", ".pptx", ".txt"}


@router.post("/upload")
async def agent_upload(file: UploadFile = File(...)):
    """Upload a document for ingestion into the vector store."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")

    ext = Path(file.filename).suffix.lower()
    if ext not in SUPPORTED_UPLOAD_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Supported: {sorted(SUPPORTED_UPLOAD_EXTENSIONS)}",
        )

    content = await file.read()
    logger.info("Upload received: filename=%s size=%d ext=%s", file.filename, len(content), ext)

    # Parse and chunk
    if ext == ".txt":
        text = content.decode("utf-8", errors="replace")
    else:
        parser = DocumentParser()
        text = parser.parse(content, file.filename)

    parser = DocumentParser()
    chunks = parser.chunk(text)

    if not chunks:
        raise HTTPException(status_code=400, detail="No text could be extracted from the file.")

    logger.info("Parsed %d chunks from %s", len(chunks), file.filename)

    # Ingest into vector store
    file_id = f"upload-{uuid.uuid4().hex[:8]}-{file.filename}"
    vector_store = get_vector_store()

    metadata = [
        {
            "file_id": file_id,
            "filename": file.filename,
            "chunk_index": i,
            "source": "agent_upload",
        }
        for i in range(len(chunks))
    ]
    ids = [f"{file_id}_chunk_{i}" for i in range(len(chunks))]

    vector_store.add_documents(chunks, metadata, ids)
    logger.info("Ingested %d chunks for %s (file_id=%s)", len(chunks), file.filename, file_id)

    return {
        "status": "ingested",
        "filename": file.filename,
        "file_id": file_id,
        "chunks": len(chunks),
    }


# ── Download ──────────────────────────────────────────────────────────

@router.get("/download/{filename}")
async def agent_download(filename: str):
    """Download an agent-written file from agent_outputs/."""
    # Prevent path traversal
    safe_name = Path(filename).name
    if not safe_name or safe_name.startswith("."):
        raise HTTPException(status_code=400, detail="Invalid filename.")

    filepath = AGENT_OUTPUTS_DIR / safe_name
    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {safe_name}")

    mime_type, _ = mimetypes.guess_type(safe_name)
    if mime_type is None:
        mime_type = "application/octet-stream"

    return FileResponse(
        path=str(filepath),
        filename=safe_name,
        media_type=mime_type,
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
    )
