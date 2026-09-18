from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Property
from app.domain.enums import AvailabilityStatus, CommercialStatus, OperationType


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
        commercial_status: CommercialStatus | None = None,
    ) -> tuple[list[Property], int]:
        filters = []
        if operation_type:
            filters.append(Property.operation_type == operation_type.value)
        if city:
            filters.append(func.lower(Property.city) == city.casefold())
        if availability:
            filters.append(Property.availability_status == availability.value)
        if commercial_status:
            filters.append(Property.commercial_status == commercial_status.value)

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

    async def create(self, record: dict[str, object]) -> Property:
        prop = Property(**record)
        self.session.add(prop)
        await self.session.commit()
        await self.session.refresh(prop)
        return prop

    async def update(self, prop: Property, updates: dict[str, object]) -> Property:
        for key, value in updates.items():
            setattr(prop, key, value)
        await self.session.commit()
        await self.session.refresh(prop)
        return prop
