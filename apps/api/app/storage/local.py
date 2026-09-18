import hashlib
from pathlib import Path
from uuid import UUID, uuid4

from app.core.errors import NotFoundError
from app.core.settings import REPOSITORY_ROOT
from app.storage.contracts import PropertyMediaStorage


class LocalFilesystemStorage(PropertyMediaStorage):
    """Local filesystem storage implementation for property media assets."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or (REPOSITORY_ROOT / ".local" / "media")
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def store(
        self,
        *,
        property_id: UUID,
        filename: str,
        content: bytes,
        mime_type: str,
    ) -> str:
        safe_prefix = uuid4().hex[:12]
        content_hash = hashlib.sha256(content).hexdigest()[:8]
        extension = Path(filename).suffix.lower() or ".jpg"
        storage_key = f"{property_id}/{safe_prefix}_{content_hash}{extension}"

        target_path = self.base_dir / storage_key
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(content)
        return storage_key

    async def retrieve(self, storage_key: str) -> bytes:
        target_path = (self.base_dir / storage_key).resolve()
        if not target_path.is_relative_to(self.base_dir.resolve()):
            raise NotFoundError("Archivo no encontrado")
        if not target_path.is_file():
            raise NotFoundError("Archivo no encontrado")
        return target_path.read_bytes()

    async def delete(self, storage_key: str) -> None:
        target_path = (self.base_dir / storage_key).resolve()
        if target_path.is_relative_to(self.base_dir.resolve()) and target_path.is_file():
            target_path.unlink()

    def get_url(self, storage_key: str) -> str:
        return f"/api/media/{storage_key}"
