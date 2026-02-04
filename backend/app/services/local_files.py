from pathlib import Path
from typing import List, Tuple
import mimetypes
import hashlib

from app.services.document_source import DocumentSource, Folder, File


class LocalFileSource(DocumentSource):
    """Document source that reads from local file system (mock mode)."""

    def __init__(self, base_path: Path):
        self.base_path = Path(base_path).resolve()
        if not self.base_path.exists():
            self.base_path.mkdir(parents=True, exist_ok=True)

    def _path_to_id(self, path: Path) -> str:
        """Convert a path to a stable ID."""
        relative = path.relative_to(self.base_path)
        return hashlib.md5(str(relative).encode()).hexdigest()

    def _id_to_path(self, folder_id: str) -> Path:
        """Find path by searching for matching ID."""
        base_resolved = self.base_path.resolve()
        for path in self.base_path.rglob("*"):
            if self._path_to_id(path) == folder_id:
                resolved = path.resolve()
                # Ensure path is within base_path (prevent traversal)
                if not str(resolved).startswith(str(base_resolved)):
                    raise ValueError("Path traversal detected")
                return resolved
        raise ValueError(f"No path found for ID: {folder_id}")

    def _validate_path_within_base(self, path: Path) -> Path:
        """Validate that a path is within the base path to prevent traversal attacks."""
        resolved = path.resolve()
        base_resolved = self.base_path.resolve()
        if not str(resolved).startswith(str(base_resolved)):
            raise ValueError("Path traversal detected")
        return resolved

    async def list_folders(self, parent_id: str | None = None) -> List[Folder]:
        """List folders. parent_id=None returns root folders."""
        if parent_id is None:
            search_path = self.base_path
        else:
            search_path = self._id_to_path(parent_id)

        folders = []
        for item in search_path.iterdir():
            if item.is_dir():
                folders.append(
                    Folder(
                        id=self._path_to_id(item),
                        name=item.name,
                        path=str(item.relative_to(self.base_path)),
                    )
                )

        return sorted(folders, key=lambda f: f.name)

    async def list_files(self, folder_id: str) -> List[File]:
        """List files in a folder."""
        folder_path = self._id_to_path(folder_id)

        files = []
        for item in folder_path.iterdir():
            if item.is_file():
                mime_type, _ = mimetypes.guess_type(str(item))
                files.append(
                    File(
                        id=self._path_to_id(item),
                        name=item.name,
                        path=str(item.relative_to(self.base_path)),
                        mime_type=mime_type or "application/octet-stream",
                        size=item.stat().st_size,
                    )
                )

        return sorted(files, key=lambda f: f.name)

    async def download_file(self, file_id: str) -> Tuple[bytes, str]:
        """Download file content. Returns (bytes, filename)."""
        file_path = self._id_to_path(file_id)
        # Additional validation for file downloads
        self._validate_path_within_base(file_path)
        return file_path.read_bytes(), file_path.name
