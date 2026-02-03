"""Data Room service layer."""
from app.services.document_source import get_document_source
from app.services.document_parser import DocumentParser
from app.services.vector_store import VectorStore


class DataRoomService:
    """Service for Data Room operations."""
    
    def __init__(self):
        self.source = get_document_source()
        self.parser = DocumentParser()
        self.vector_store = VectorStore()
    
    async def list_folders(self, parent_id: str | None = None):
        """List available folders."""
        return await self.source.list_folders(parent_id)
    
    async def list_files(self, folder_id: str):
        """List files in a folder."""
        return await self.source.list_files(folder_id)
    
    async def ingest_file(self, file_id: str, folder_id: str) -> dict:
        """Ingest a single file into the vector store."""
        content, filename = await self.source.download_file(file_id)
        text = self.parser.parse(content, filename)
        chunks = self.parser.chunk(text)
        
        if not chunks:
            return {"file": filename, "status": "skipped", "reason": "No text extracted"}
        
        ids = [f"{file_id}_chunk_{i}" for i in range(len(chunks))]
        metadata = [
            {
                "file_id": file_id,
                "filename": filename,
                "chunk_index": i,
                "folder_id": folder_id
            }
            for i in range(len(chunks))
        ]
        
        self.vector_store.add_documents(chunks, metadata, ids)
        return {"file": filename, "status": "success", "chunks": len(chunks)}
