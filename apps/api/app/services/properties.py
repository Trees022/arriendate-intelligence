from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.db.models import Property
from app.domain.enums import AvailabilityStatus, OperationType
from app.repositories.properties import PropertyRepository


class PropertyService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = PropertyRepository(session)

    async def get(self, property_id: UUID) -> Property:
        property_record = await self.repository.get(property_id)
        if not property_record:
            raise NotFoundError("Propiedad no encontrada")
        return property_record

    async def list(
        self,
        *,
        page: int,
        page_size: int,
        operation_type: OperationType | None,
        city: str | None,
        availability: AvailabilityStatus | None,
    ) -> tuple[list[Property], int]:
        return await self.repository.list(
            page=page,
            page_size=page_size,
            operation_type=operation_type,
            city=city,
            availability=availability,
        )
