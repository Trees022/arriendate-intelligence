from typing import cast
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import LeadCreate
from app.db.models import Lead


class LeadRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, lead_id: UUID) -> Lead | None:
        return await self.session.get(Lead, lead_id)

    async def list(self, *, page: int, page_size: int) -> tuple[list[Lead], int]:
        rows = await self.session.scalars(
            select(Lead)
            .order_by(Lead.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        total = await self.session.scalar(select(func.count()).select_from(Lead))
        return list(rows), int(total or 0)

    async def get_by_idempotency_key(self, key: UUID) -> Lead | None:
        return cast(
            Lead | None,
            await self.session.scalar(select(Lead).where(Lead.idempotency_key == key)),
        )

    async def create_or_get(self, payload: LeadCreate, idempotency_key: UUID) -> Lead:
        existing = await self.get_by_idempotency_key(idempotency_key)
        if existing is not None:
            return existing

        lead = Lead(
            name=payload.name,
            email=str(payload.email).lower() if payload.email else None,
            phone=payload.phone,
            original_request=payload.original_request,
            idempotency_key=idempotency_key,
        )
        self.session.add(lead)
        try:
            await self.session.commit()
        except IntegrityError:
            # The pre-read is an optimization, not a concurrency guarantee. PostgreSQL can
            # serialize two inserts at the unique constraint, so recover the winning row.
            await self.session.rollback()
            existing = await self.get_by_idempotency_key(idempotency_key)
            if existing is None:
                raise
            return existing
        await self.session.refresh(lead)
        return lead
