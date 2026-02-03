from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from app.services.document_source import get_document_source
from app.services.document_parser import DocumentParser
from app.services.vector_store import VectorStore
from app.agents.camel_agent import CamelRAGAgent
from app.agents.simple_agent import SimpleChatAgent
from app.services.event_bus import event_bus
from app.core.config import settings

router = APIRouter(prefix="/data-room", tags=["data-room"])


class IngestRequest(BaseModel):
    folder_id: str


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    sources: List[dict]


@router.get("/folders")
async def list_folders(parent_id: Optional[str] = None):
    """List folders from document source."""
    source = get_document_source()
    folders = await source.list_folders(parent_id)
    return {"folders": [f.model_dump() for f in folders]}


@router.get("/folders/{folder_id}/files")
async def list_files(folder_id: str):
    """List files in a folder."""
    source = get_document_source()
    files = await source.list_files(folder_id)
    return {"files": [f.model_dump() for f in files]}


@router.post("/ingest")
async def ingest_folder(request: IngestRequest):
    """Ingest all documents from a folder into the vector store."""
    source = get_document_source()
    parser = DocumentParser()
    vector_store = VectorStore()
    
    files = await source.list_files(request.folder_id)
    results = []
    
    for file in files:
        try:
            # Check if file type is supported
            if not any(file.name.lower().endswith(ext) for ext in ['.pdf', '.docx', '.pptx']):
                results.append({
                    "file": file.name, 
                    "status": "skipped", 
                    "reason": "Unsupported file type"
                })
                continue
            
            content, filename = await source.download_file(file.id)
            text = parser.parse(content, filename)
            chunks = parser.chunk(text)
            
            if not chunks:
                results.append({
                    "file": filename, 
                    "status": "skipped", 
                    "reason": "No text extracted"
                })
                continue
            
            ids = [f"{file.id}_chunk_{i}" for i in range(len(chunks))]
            metadata = [
                {
                    "file_id": file.id, 
                    "filename": filename, 
                    "chunk_index": i,
                    "folder_id": request.folder_id
                } 
                for i in range(len(chunks))
            ]
            
            vector_store.add_documents(chunks, metadata, ids)
            results.append({
                "file": filename, 
                "status": "success", 
                "chunks": len(chunks)
            })
            
        except Exception as e:
            results.append({
                "file": file.name, 
                "status": "error", 
                "error": str(e)
            })
    
    return {"results": results}


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat with the ingested documents using RAG."""
    vector_store = VectorStore()
    
    # Use CAMEL agent by default, fall back to simple agent if configured
    use_simple = settings.use_simple_agent
    agent = SimpleChatAgent() if use_simple else CamelRAGAgent()
    
    # Search for relevant context
    search_results = vector_store.search(request.message, n_results=5)
    
    if not search_results:
        return ChatResponse(
            response="I don't have any documents to search. Please ingest some documents first.",
            sources=[]
        )
    
    context = [r["text"] for r in search_results]
    sources = [r["metadata"] for r in search_results]
    
    # Collect response
    response_chunks = []
    
    async def emit_event(event):
        await event_bus.broadcast(event.model_dump())
    
    async for chunk in agent.chat(request.message, context, emit_event):
        response_chunks.append(chunk)
    
    return ChatResponse(
        response="".join(response_chunks),
        sources=sources
    )


@router.delete("/documents")
async def clear_documents():
    """Clear all ingested documents."""
    vector_store = VectorStore()
    vector_store.clear()
    return {"status": "cleared"}
