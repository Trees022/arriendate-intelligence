from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.dependencies import SessionDep
from app.api.schemas import PublicationTargetCreate, PublicationTargetResponse
from app.services.publication_targets import PublicationTargetService

router = APIRouter(prefix="/publication-targets", tags=["publication_targets"])


@router.get("", response_model=list[PublicationTargetResponse])
async def list_publication_targets(
    session: SessionDep,
    active_only: bool = Query(default=False),
) -> list[PublicationTargetResponse]:
    service = PublicationTargetService(session)
    targets = await service.list(active_only=active_only)
    return [PublicationTargetResponse.model_validate(t) for t in targets]


@router.post(
    "",
    response_model=PublicationTargetResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_publication_target(
    payload: PublicationTargetCreate,
    session: SessionDep,
) -> PublicationTargetResponse:
    service = PublicationTargetService(session)
    target = await service.create(payload)
    return PublicationTargetResponse.model_validate(target)


@router.get("/{target_id}", response_model=PublicationTargetResponse)
async def get_publication_target(
    target_id: UUID,
    session: SessionDep,
) -> PublicationTargetResponse:
    service = PublicationTargetService(session)
    target = await service.get(target_id)
    return PublicationTargetResponse.model_validate(target)
