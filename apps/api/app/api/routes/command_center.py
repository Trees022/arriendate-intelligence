from uuid import UUID

from fastapi import APIRouter

from app.api.dependencies import SessionDep, StorageDep
from app.api.schemas import PropertyCommandCenterResponse
from app.services.command_center import PropertyCommandCenterService

router = APIRouter(tags=["property_command_center"])


@router.get(
    "/properties/{property_id}/command-center",
    response_model=PropertyCommandCenterResponse,
)
async def get_property_command_center(
    property_id: UUID,
    session: SessionDep,
    storage: StorageDep,
) -> PropertyCommandCenterResponse:
    return await PropertyCommandCenterService(session, storage).get(property_id)

