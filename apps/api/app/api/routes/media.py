from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Response, UploadFile, status

from app.api.dependencies import SessionDep, StorageDep
from app.api.schemas import (
    PropertyMediaReorderRequest,
    PropertyMediaResponse,
    PropertyMediaUpdateRequest,
)
from app.core.media import MAX_MEDIA_FILE_SIZE_BYTES
from app.services.media import PropertyMediaService

router = APIRouter(tags=["media"])


@router.post(
    "/properties/{property_id}/media",
    response_model=PropertyMediaResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_property_media(
    property_id: UUID,
    session: SessionDep,
    storage: StorageDep,
    file: Annotated[UploadFile, File()],
) -> PropertyMediaResponse:
    content = await file.read(MAX_MEDIA_FILE_SIZE_BYTES + 1)
    filename = file.filename or "photo.jpg"
    mime_type = file.content_type or "image/jpeg"

    service = PropertyMediaService(session, storage)
    return await service.upload(
        property_id=property_id,
        filename=filename,
        content=content,
        mime_type=mime_type,
    )


@router.get(
    "/properties/{property_id}/media",
    response_model=list[PropertyMediaResponse],
)
async def list_property_media(
    property_id: UUID,
    session: SessionDep,
    storage: StorageDep,
) -> list[PropertyMediaResponse]:
    service = PropertyMediaService(session, storage)
    return await service.list_by_property(property_id)


@router.patch(
    "/properties/{property_id}/media/reorder",
    response_model=list[PropertyMediaResponse],
)
async def reorder_property_media(
    property_id: UUID,
    payload: PropertyMediaReorderRequest,
    session: SessionDep,
    storage: StorageDep,
) -> list[PropertyMediaResponse]:
    service = PropertyMediaService(session, storage)
    return await service.reorder(property_id, payload.media_ids)


@router.patch(
    "/properties/{property_id}/media/{media_id}",
    response_model=PropertyMediaResponse,
)
async def update_property_media(
    property_id: UUID,
    media_id: UUID,
    payload: PropertyMediaUpdateRequest,
    session: SessionDep,
    storage: StorageDep,
) -> PropertyMediaResponse:
    service = PropertyMediaService(session, storage)
    if payload.is_cover:
        return await service.set_cover(property_id, media_id)
    # If other updates in future, handled here
    media_list = await service.list_by_property(property_id)
    for m in media_list:
        if m.id == media_id:
            return m
    return await service.set_cover(property_id, media_id)


@router.delete(
    "/properties/{property_id}/media/{media_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_property_media(
    property_id: UUID,
    media_id: UUID,
    session: SessionDep,
    storage: StorageDep,
) -> None:
    service = PropertyMediaService(session, storage)
    await service.delete(property_id, media_id)


@router.get("/media/{storage_key:path}")
async def serve_media(
    storage_key: str,
    storage: StorageDep,
) -> Response:
    content = await storage.retrieve(storage_key)
    # Determine mime type from extension
    mime = "image/jpeg"
    if storage_key.endswith(".png"):
        mime = "image/png"
    elif storage_key.endswith(".webp"):
        mime = "image/webp"
    return Response(
        content=content,
        media_type=mime,
        headers={"Cache-Control": "public, max-age=86400"},
    )
