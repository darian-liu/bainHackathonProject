from typing import List, Tuple
from dataclasses import dataclass

from app.services.document_source import DocumentSource, File
from app.services.document_parser import DocumentParser
from app.services.vector_store import get_vector_store


SUPPORTED_EXTENSIONS = [".pdf", ".docx", ".pptx", ".txt", ".md"]


@dataclass
class IngestResult:
    file: str
    status: str  # 'success', 'skipped', 'error'
    chunks: int | None = None
    reason: str | None = None
    error: str | None = None


def validate_file(file: File) -> Tuple[bool, str | None]:
    """
    Validate if a file is supported for ingestion.
    Returns (is_valid, reason_if_invalid).
    """
    if not any(file.name.lower().endswith(ext) for ext in SUPPORTED_EXTENSIONS):
        return False, "Unsupported file type"
    return True, None


async def process_file(
    source: DocumentSource,
    parser: DocumentParser,
    file: File,
    folder_id: str,
) -> Tuple[List[str], List[dict], List[str]]:
    """
    Process a single file: download, parse, and chunk.
    Returns (chunks, metadata, ids).
    """
    content, filename = await source.download_file(file.id)
    text = parser.parse(content, filename)
    chunks = parser.chunk(text)

    if not chunks:
        return [], [], []

    ids = [f"{file.id}_chunk_{i}" for i in range(len(chunks))]
    metadata = [
        {
            "file_id": file.id,
            "filename": filename,
            "chunk_index": i,
            "folder_id": folder_id,
        }
        for i in range(len(chunks))
    ]

    return chunks, metadata, ids


async def ingest_documents(
    source: DocumentSource,
    folder_id: str,
) -> List[IngestResult]:
    """
    Ingest all documents from a folder into the vector store.
    Returns list of results per file.
    """
    parser = DocumentParser()
    vector_store = get_vector_store()

    files = await source.list_files(folder_id)
    results: List[IngestResult] = []

    for file in files:
        try:
            # Validate file type
            is_valid, reason = validate_file(file)
            if not is_valid:
                results.append(
                    IngestResult(file=file.name, status="skipped", reason=reason)
                )
                continue

            # Process file
            chunks, metadata, ids = await process_file(
                source, parser, file, folder_id
            )

            if not chunks:
                results.append(
                    IngestResult(
                        file=file.name, status="skipped", reason="No text extracted"
                    )
                )
                continue

            # Add to vector store
            vector_store.add_documents(chunks, metadata, ids)
            results.append(
                IngestResult(file=file.name, status="success", chunks=len(chunks))
            )

        except Exception as e:
            results.append(IngestResult(file=file.name, status="error", error=str(e)))

    return results


async def ingest_single_file(
    file_path: str,
    filename: str,
    vector_store=None,
    folder_id: str = "uploads"
) -> IngestResult:
    """
    Ingest a single file from a local path.

    Args:
        file_path: Path to the file to ingest
        filename: Original filename
        vector_store: Optional vector store (uses default if not provided)
        folder_id: Folder ID for metadata

    Returns:
        IngestResult with status and chunk count
    """
    import secrets

    if vector_store is None:
        vector_store = get_vector_store()

    parser = DocumentParser()

    try:
        # Check file extension
        if not any(filename.lower().endswith(ext) for ext in SUPPORTED_EXTENSIONS):
            return IngestResult(
                file=filename,
                status="skipped",
                reason="Unsupported file type"
            )

        # Read file content
        with open(file_path, "rb") as f:
            content = f.read()

        # Parse and chunk
        text = parser.parse(content, filename)
        chunks = parser.chunk(text)

        if not chunks:
            return IngestResult(
                file=filename,
                status="skipped",
                reason="No text extracted"
            )

        # Generate file ID
        file_id = secrets.token_urlsafe(16)

        # Create IDs and metadata
        ids = [f"{file_id}_chunk_{i}" for i in range(len(chunks))]
        metadata = [
            {
                "file_id": file_id,
                "filename": filename,
                "chunk_index": i,
                "folder_id": folder_id,
            }
            for i in range(len(chunks))
        ]

        # Add to vector store
        vector_store.add_documents(chunks, metadata, ids)

        return IngestResult(
            file=filename,
            status="success",
            chunks=len(chunks)
        )

    except Exception as e:
        return IngestResult(
            file=filename,
            status="error",
            error=str(e)
        )
