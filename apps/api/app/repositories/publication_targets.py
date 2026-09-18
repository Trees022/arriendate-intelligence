from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import PublicationTarget


class PublicationTargetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, target_id: UUID) -> PublicationTarget | None:
        return await self.session.get(PublicationTarget, target_id)

    async def list(
        self, *, active_only: bool = False
    ) -> list[PublicationTarget]:
        stmt = select(PublicationTarget)
        if active_only:
            stmt = stmt.where(PublicationTarget.active.is_(True))
        stmt = stmt.order_by(
            PublicationTarget.channel_type.asc(),
            PublicationTarget.name.asc(),
        )
        rows = await self.session.scalars(stmt)
        return list(rows)

    async def create(self, record: dict[str, object]) -> PublicationTarget:
        target = PublicationTarget(**record)
        self.session.add(target)
        await self.session.commit()
        await self.session.refresh(target)
        return target

    async def update(
        self, target: PublicationTarget, updates: dict[str, object]
    ) -> PublicationTarget:
        for key, value in updates.items():
            setattr(target, key, value)
        await self.session.commit()
        await self.session.refresh(target)
        return target
