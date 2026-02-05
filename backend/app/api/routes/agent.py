"""Agent API routes for document analysis agent."""

from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from pathlib import Path
import tempfile
import os

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.agents.document_agent import DocumentAgent
from app.services.event_bus import event_bus
from app.services.document_source import get_document_source
from app.services.ingestion_service import ingest_documents

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/agent", tags=["agent"])

# Store agent instances per session
_agent_sessions: Dict[str, DocumentAgent] = {}


def get_agent(session_id: str = "default") -> DocumentAgent:
    """Get or create an agent for a session."""
    if session_id not in _agent_sessions:
        _agent_sessions[session_id] = DocumentAgent()
    return _agent_sessions[session_id]


# Request/Response Models
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"


class ToolCall(BaseModel):
    id: str
    name: str
    arguments: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    response: str
    session_id: str
    tool_calls: List[ToolCall]


class ToolInfo(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]


class ToolsResponse(BaseModel):
    tools: List[ToolInfo]


# ============== Endpoints ============== #

@router.post("/chat", response_model=ChatResponse)
@limiter.limit("30/minute")
async def agent_chat(request: Request, body: ChatRequest):
    """Send a message to the document agent.

    The agent can use tools to:
    - List available documents
    - Search across documents
    - Read specific documents
    - Summarize documents
    - Write new documents

    Returns the response along with any tool calls that were made.
    """
    agent = get_agent(body.session_id or "default")

    tool_calls_made: List[ToolCall] = []

    async def emit_event(event):
        """Capture tool calls and broadcast events."""
        event_data = event.model_dump()
        await event_bus.broadcast(event_data)

        # Track tool calls
        if event.type.value == "tool_called":
            tool_calls_made.append(ToolCall(
                id=event_data.get("data", {}).get("tool_call_id", ""),
                name=event_data.get("data", {}).get("tool", ""),
                arguments=event_data.get("data", {}).get("arguments", {}),
                result=None
            ))
        elif event.type.value == "tool_completed":
            # Update the last tool call with its result
            tool_call_id = event_data.get("data", {}).get("tool_call_id", "")
            for tc in tool_calls_made:
                if tc.id == tool_call_id:
                    tc.result = {"success": event_data.get("data", {}).get("success", False)}

    try:
        # Collect response
        response_chunks = []
        async for chunk in agent.chat(body.message, [], emit_event):
            response_chunks.append(chunk)

        return ChatResponse(
            response="".join(response_chunks),
            session_id=body.session_id or "default",
            tool_calls=tool_calls_made
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent chat failed: {str(e)}")


@router.post("/upload")
@limiter.limit("10/minute")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    session_id: str = "default"
):
    """Upload and ingest a new document for the agent to use.

    Supports various file types: PDF, TXT, MD, DOCX, etc.
    The document will be chunked and added to the vector store.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    # Save to temp file
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, file.filename)

    try:
        content = await file.read()
        with open(temp_path, "wb") as f:
            f.write(content)

        # Get document source and ingest
        source = get_document_source()

        # For local files mode, we can directly ingest the temp file
        # For other modes, we'd need to upload to the source first
        from app.services.ingestion_service import ingest_single_file
        from app.services.vector_store import get_vector_store

        vector_store = get_vector_store()
        result = await ingest_single_file(temp_path, file.filename, vector_store)

        return {
            "success": result.status == "success",
            "filename": file.filename,
            "chunks": result.chunks,
            "status": result.status,
            "error": result.error
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

    finally:
        # Cleanup temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)


@router.get("/tools", response_model=ToolsResponse)
async def list_tools():
    """List all available tools the agent can use."""
    agent = get_agent("default")
    tools = agent.get_available_tools()

    return ToolsResponse(
        tools=[
            ToolInfo(
                name=t["name"],
                description=t["description"],
                parameters=t["parameters"]
            )
            for t in tools
        ]
    )


@router.post("/clear")
async def clear_session(session_id: str = "default"):
    """Clear the conversation history for a session."""
    if session_id in _agent_sessions:
        _agent_sessions[session_id].clear_history()

    return {"success": True, "session_id": session_id}


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Delete an agent session entirely."""
    if session_id in _agent_sessions:
        del _agent_sessions[session_id]
        return {"success": True, "deleted": True}

    return {"success": True, "deleted": False}


@router.get("/download/{filename}")
async def download_file(filename: str):
    """Download a file from agent_outputs directory.
    
    This endpoint serves files created by the write_document tool,
    triggering a browser download with the original filename.
    """
    # Sanitize filename to prevent path traversal
    safe_filename = Path(filename).name
    if not safe_filename or safe_filename.startswith('.'):
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    # Look for file in agent_outputs directory
    output_dir = Path("./agent_outputs")
    file_path = output_dir / safe_filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {safe_filename}")
    
    # Determine media type based on extension
    ext = file_path.suffix.lower()
    media_types = {
        ".txt": "text/plain",
        ".md": "text/markdown",
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    }
    media_type = media_types.get(ext, "application/octet-stream")
    
    return FileResponse(
        path=str(file_path),
        filename=safe_filename,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename=\"{safe_filename}\""}
    )


@router.get("/files")
async def list_output_files():
    """List all files in the agent_outputs directory."""
    output_dir = Path("./agent_outputs")
    
    if not output_dir.exists():
        return {"files": []}
    
    files = []
    for f in output_dir.iterdir():
        if f.is_file() and not f.name.startswith('.'):
            files.append({
                "filename": f.name,
                "size_bytes": f.stat().st_size,
                "modified": f.stat().st_mtime
            })
    
    return {"files": sorted(files, key=lambda x: x["modified"], reverse=True)}
