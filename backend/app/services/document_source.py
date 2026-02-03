from abc import ABC, abstractmethod
from typing import List, Tuple
from pydantic import BaseModel
from pathlib import Path
import os


class Folder(BaseModel):
    id: str
    name: str
    path: str


class File(BaseModel):
    id: str
    name: str
    path: str
    mime_type: str
    size: int


class DocumentSource(ABC):
    @abstractmethod
    async def list_folders(self, parent_id: str | None = None) -> List[Folder]:
        """List folders. parent_id=None returns root folders."""
        ...
    
    @abstractmethod
    async def list_files(self, folder_id: str) -> List[File]:
        """List files in a folder."""
        ...
    
    @abstractmethod
    async def download_file(self, file_id: str) -> Tuple[bytes, str]:
        """Download file content. Returns (bytes, filename)."""
        ...


def get_document_source() -> DocumentSource:
    """Factory function based on DOCUMENT_SOURCE_MODE env var."""
    from app.services.local_files import LocalFileSource
    from app.services.sharepoint import SharePointSource
    
    mode = os.getenv("DOCUMENT_SOURCE_MODE", "mock")
    if mode == "live":
        return SharePointSource()
    return LocalFileSource(Path("./demo-docs"))
