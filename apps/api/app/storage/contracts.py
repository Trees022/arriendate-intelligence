from typing import Protocol
from uuid import UUID


class PropertyMediaStorage(Protocol):
    """Abstract storage interface for property photographs and media assets."""

    async def store(
        self,
        *,
        property_id: UUID,
        filename: str,
        content: bytes,
        mime_type: str,
    ) -> str:
        """Store media bytes and return a unique storage_key."""
        ...

    async def retrieve(self, storage_key: str) -> bytes:
        """Retrieve media raw bytes by storage_key."""
        ...

    async def delete(self, storage_key: str) -> None:
        """Delete media asset from underlying storage."""
        ...

    def get_url(self, storage_key: str) -> str:
        """Return the retrieval URL for the media asset."""
        ...
