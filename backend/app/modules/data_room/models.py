"""Data models for Data Room module."""
from pydantic import BaseModel
from typing import List, Optional


class FolderInfo(BaseModel):
    id: str
    name: str
    path: str


class FileInfo(BaseModel):
    id: str
    name: str
    path: str
    mime_type: str
    size: int


class IngestResult(BaseModel):
    file: str
    status: str
    chunks: Optional[int] = None
    reason: Optional[str] = None
    error: Optional[str] = None


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatSession(BaseModel):
    id: str
    messages: List[ChatMessage]
