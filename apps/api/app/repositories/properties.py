from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Property
from app.domain.enums import AvailabilityStatus, OperationType


class PropertyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, property_id: UUID) -> Property | None:
        return await self.session.get(Property, property_id)

    async def list(
        self,
        *,
        page: int,
        page_size: int,
        operation_type: OperationType | None,
        city: str | None,
        availability: AvailabilityStatus | None,
    ) -> tuple[list[Property], int]:
        filters = []
        if operation_type:
            filters.append(Property.operation_type == operation_type.value)
        if city:
            filters.append(func.lower(Property.city) == city.casefold())
        if availability:
            filters.append(Property.availability_status == availability.value)

        total = await self.session.scalar(
            select(func.count()).select_from(Property).where(*filters)
        )
        rows = await self.session.scalars(
            select(Property)
            .where(*filters)
            .order_by(Property.city, Property.title, Property.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(rows), int(total or 0)
