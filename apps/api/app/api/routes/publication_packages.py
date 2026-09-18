from uuid import UUID

from fastapi import APIRouter, status

from app.api.dependencies import SessionDep
from app.api.schemas import PublicationPackageResponse
from app.services.publication_packages import PublicationPackageService

router = APIRouter(tags=["publication_packages"])


@router.post(
    "/properties/{property_id}/packages",
    response_model=PublicationPackageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_publication_package(
    property_id: UUID,
    session: SessionDep,
) -> PublicationPackageResponse:
    service = PublicationPackageService(session)
    return await service.generate_package(property_id)


@router.get(
    "/properties/{property_id}/packages",
    response_model=list[PublicationPackageResponse],
)
async def list_publication_packages(
    property_id: UUID,
    session: SessionDep,
) -> list[PublicationPackageResponse]:
    service = PublicationPackageService(session)
    return await service.list_by_property(property_id)


@router.get(
    "/packages/{package_id}",
    response_model=PublicationPackageResponse,
)
async def get_publication_package(
    package_id: UUID,
    session: SessionDep,
) -> PublicationPackageResponse:
    service = PublicationPackageService(session)
    return await service.get_package(package_id)


@router.patch(
    "/packages/{package_id}/approve",
    response_model=PublicationPackageResponse,
)
async def approve_publication_package(
    package_id: UUID,
    session: SessionDep,
) -> PublicationPackageResponse:
    service = PublicationPackageService(session)
    return await service.approve_package(package_id)


@router.get("/packages/{package_id}/stale")
async def check_package_staleness(
    package_id: UUID,
    session: SessionDep,
) -> dict[str, bool]:
    service = PublicationPackageService(session)
    stale = await service.is_stale(package_id)
    return {"is_stale": stale}
