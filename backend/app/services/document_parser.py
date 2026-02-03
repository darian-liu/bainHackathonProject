from pathlib import Path
from typing import List
import tempfile
import os


class DocumentParser:
    """Parse documents using the unstructured library."""
    
    SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".pptx"}
    
    def parse(self, content: bytes, filename: str) -> str:
        """Parse document bytes into text."""
        from unstructured.partition.auto import partition
        
        ext = Path(filename).suffix.lower()
        if ext not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {ext}. Supported: {self.SUPPORTED_EXTENSIONS}")
        
        # Write to temp file for unstructured to process
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            elements = partition(filename=tmp_path)
            return "\n\n".join(str(el) for el in elements)
        finally:
            os.unlink(tmp_path)
    
    def chunk(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Split text into overlapping chunks for embedding."""
        if not text:
            return []
        
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            if chunk.strip():
                chunks.append(chunk)
            start = end - overlap
        return chunks
