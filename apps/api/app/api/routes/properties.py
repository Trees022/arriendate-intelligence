from uuid import UUID

from fastapi import APIRouter, Query

from app.api.dependencies import SessionDep
from app.api.schemas import PropertyListResponse, PropertyResponse
from app.domain.enums import AvailabilityStatus, OperationType
from app.services.properties import PropertyService

router = APIRouter(prefix="/properties", tags=["properties"])


@router.get("", response_model=PropertyListResponse)
async def list_properties(
    session: SessionDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=24, ge=1, le=100),
    operation_type: OperationType | None = None,
    city: str | None = Query(default=None, min_length=2, max_length=100),
    availability: AvailabilityStatus | None = None,
) -> PropertyListResponse:
    properties, total = await PropertyService(session).list(
        page=page,
        page_size=page_size,
        operation_type=operation_type,
        city=city,
        availability=availability,
    )
    return PropertyListResponse(
        items=[PropertyResponse.model_validate(item) for item in properties],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{property_id}", response_model=PropertyResponse)
async def get_property(
    property_id: UUID,
    session: SessionDep,
) -> PropertyResponse:
    property_record = await PropertyService(session).get(property_id)
    return PropertyResponse.model_validate(property_record)
