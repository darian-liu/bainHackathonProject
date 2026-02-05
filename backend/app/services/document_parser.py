from pathlib import Path
from typing import List
import tempfile
import os


class DocumentParser:
    """Parse documents - plain text directly, complex formats via unstructured."""
    
    # All supported extensions
    SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".txt", ".md"}
    
    # Extensions that need unstructured library
    COMPLEX_EXTENSIONS = {".pdf", ".docx", ".pptx"}
    
    # Plain text extensions (read directly)
    TEXT_EXTENSIONS = {".txt", ".md"}
    
    def parse(self, content: bytes, filename: str) -> str:
        """Parse document bytes into text."""
        ext = Path(filename).suffix.lower()
        
        if ext not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {ext}. Supported: {self.SUPPORTED_EXTENSIONS}")
        
        # Handle plain text files directly
        if ext in self.TEXT_EXTENSIONS:
            try:
                return content.decode("utf-8")
            except UnicodeDecodeError:
                # Try other encodings
                for encoding in ["latin-1", "cp1252"]:
                    try:
                        return content.decode(encoding)
                    except UnicodeDecodeError:
                        continue
                raise ValueError(f"Could not decode {filename} as text")
        
        # Handle complex formats with unstructured
        try:
            from unstructured.partition.auto import partition
        except ImportError:
            raise ValueError("unstructured library not installed. Run: pip install unstructured[pdf,docx,pptx]")
        
        # Write to temp file for unstructured to process
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            elements = partition(filename=tmp_path)
            text = "\n\n".join(str(el) for el in elements)
            if not text.strip():
                raise ValueError(f"No text extracted from {filename}. The file may be empty or corrupted.")
            return text
        except Exception as e:
            raise ValueError(f"Failed to parse {filename}: {str(e)}")
        finally:
            if os.path.exists(tmp_path):
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
