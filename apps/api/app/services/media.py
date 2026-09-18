from __future__ import annotations

from pathlib import Path
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import PropertyMediaResponse
from app.core.errors import NotFoundError, ValidationError
from app.core.media import (
    ALLOWED_MEDIA_EXTENSIONS,
    ALLOWED_MEDIA_MIME_TYPES,
    MAX_MEDIA_FILE_SIZE_BYTES,
)
from app.db.models import PropertyMedia
from app.repositories.media import PropertyMediaRepository
from app.repositories.properties import PropertyRepository
from app.storage.contracts import PropertyMediaStorage


class PropertyMediaService:
    def __init__(
        self, session: AsyncSession, storage: PropertyMediaStorage
    ) -> None:
        self.session = session
        self.storage = storage
        self.repository = PropertyMediaRepository(session)
        self.property_repository = PropertyRepository(session)

    async def upload(
        self,
        *,
        property_id: UUID,
        filename: str,
        content: bytes,
        mime_type: str,
    ) -> PropertyMediaResponse:
        prop = await self.property_repository.get(property_id)
        if not prop:
            raise NotFoundError("Propiedad no encontrada")

        if len(filename) > 255:
            raise ValidationError("El nombre del archivo excede 255 caracteres")

        size_bytes = len(content)
        if size_bytes <= 0:
            raise ValidationError("El archivo está vacío")
        if size_bytes > MAX_MEDIA_FILE_SIZE_BYTES:
            limit_mb = MAX_MEDIA_FILE_SIZE_BYTES // (1024 * 1024)
            raise ValidationError(
                f"El archivo excede el límite máximo de {limit_mb}MB"
            )

        # Validate mime type and extension
        ext = Path(filename).suffix.lower()
        if mime_type not in ALLOWED_MEDIA_MIME_TYPES or ext not in ALLOWED_MEDIA_EXTENSIONS:
            raise ValidationError(
                "Tipo de archivo no permitido. Solo se admiten formatos JPEG, PNG y WebP"
            )

        existing_count = await self.repository.count_by_property(property_id)
        is_cover = existing_count == 0

        storage_key = await self.storage.store(
            property_id=property_id,
            filename=filename,
            content=content,
            mime_type=mime_type,
        )

        record: dict[str, object] = {
            "property_id": property_id,
            "storage_key": storage_key,
            "original_filename": filename,
            "media_type": "image",
            "mime_type": mime_type,
            "size_bytes": size_bytes,
            "position": existing_count,
            "is_cover": is_cover,
        }
        media = await self.repository.create(record)
        return self._to_response(media)

    async def list_by_property(
        self, property_id: UUID
    ) -> list[PropertyMediaResponse]:
        prop = await self.property_repository.get(property_id)
        if not prop:
            raise NotFoundError("Propiedad no encontrada")
        items = await self.repository.list_by_property(property_id)
        return [self._to_response(item) for item in items]

    async def delete(self, property_id: UUID, media_id: UUID) -> None:
        media = await self.repository.get_by_property_and_id(property_id, media_id)
        if not media:
            raise NotFoundError("Medio no encontrado")

        was_cover = media.is_cover
        storage_key = media.storage_key

        await self.repository.delete(media)
        await self.storage.delete(storage_key)

        if was_cover:
            remaining = await self.repository.list_by_property(property_id)
            if remaining:
                await self.repository.set_cover(property_id, remaining[0].id)

    async def set_cover(
        self, property_id: UUID, media_id: UUID
    ) -> PropertyMediaResponse:
        media = await self.repository.get_by_property_and_id(property_id, media_id)
        if not media:
            raise NotFoundError("Medio no encontrado")
        updated = await self.repository.set_cover(property_id, media_id)
        return self._to_response(updated)

    async def reorder(
        self, property_id: UUID, ordered_ids: list[UUID]
    ) -> list[PropertyMediaResponse]:
        prop = await self.property_repository.get(property_id)
        if not prop:
            raise NotFoundError("Propiedad no encontrada")
        existing = await self.repository.list_by_property(property_id)
        existing_ids = {item.id for item in existing}
        if len(ordered_ids) != len(set(ordered_ids)):
            raise ValidationError("El orden de fotos no puede contener duplicados")
        if set(ordered_ids) != existing_ids:
            raise ValidationError(
                "El nuevo orden debe incluir exactamente todas las fotos de la propiedad"
            )
        items = await self.repository.reorder(property_id, ordered_ids)
        return [self._to_response(item) for item in items]

    def _to_response(self, media: PropertyMedia) -> PropertyMediaResponse:
        return PropertyMediaResponse(
            id=media.id,
            property_id=media.property_id,
            storage_key=media.storage_key,
            original_filename=media.original_filename,
            media_type=media.media_type,
            mime_type=media.mime_type,
            size_bytes=media.size_bytes,
            position=media.position,
            is_cover=media.is_cover,
            url=self.storage.get_url(media.storage_key),
            created_at=media.created_at,
        )
