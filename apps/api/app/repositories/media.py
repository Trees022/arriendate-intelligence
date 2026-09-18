from typing import cast
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import PropertyMedia


class PropertyMediaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_by_property(self, property_id: UUID) -> list[PropertyMedia]:
        rows = await self.session.scalars(
            select(PropertyMedia)
            .where(PropertyMedia.property_id == property_id)
            .order_by(PropertyMedia.position.asc(), PropertyMedia.created_at.asc())
        )
        return list(rows)

    async def get(self, media_id: UUID) -> PropertyMedia | None:
        return await self.session.get(PropertyMedia, media_id)

    async def get_by_property_and_id(
        self, property_id: UUID, media_id: UUID
    ) -> PropertyMedia | None:
        return cast(
            PropertyMedia | None,
            await self.session.scalar(
                select(PropertyMedia).where(
                    PropertyMedia.property_id == property_id,
                    PropertyMedia.id == media_id,
                )
            ),
        )

    async def count_by_property(self, property_id: UUID) -> int:
        rows = await self.list_by_property(property_id)
        return len(rows)

    async def create(self, record: dict[str, object]) -> PropertyMedia:
        media = PropertyMedia(**record)
        self.session.add(media)
        await self.session.commit()
        await self.session.refresh(media)
        return media

    async def update(
        self, media: PropertyMedia, updates: dict[str, object]
    ) -> PropertyMedia:
        for key, value in updates.items():
            setattr(media, key, value)
        await self.session.commit()
        await self.session.refresh(media)
        return media

    async def delete(self, media: PropertyMedia) -> None:
        await self.session.delete(media)
        await self.session.commit()

    async def set_cover(self, property_id: UUID, media_id: UUID) -> PropertyMedia:
        # Reset all covers for this property
        await self.session.execute(
            update(PropertyMedia)
            .where(PropertyMedia.property_id == property_id)
            .values(is_cover=False)
        )
        target = await self.get_by_property_and_id(property_id, media_id)
        if target:
            target.is_cover = True
        await self.session.commit()
        if target:
            await self.session.refresh(target)
            return target
        raise ValueError("Media not found")

    async def reorder(
        self, property_id: UUID, ordered_ids: list[UUID]
    ) -> list[PropertyMedia]:
        for idx, media_id in enumerate(ordered_ids):
            await self.session.execute(
                update(PropertyMedia)
                .where(
                    PropertyMedia.property_id == property_id,
                    PropertyMedia.id == media_id,
                )
                .values(position=idx)
            )
        await self.session.commit()
        return await self.list_by_property(property_id)
