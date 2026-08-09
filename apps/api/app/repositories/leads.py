from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import LeadCreate
from app.db.models import Lead


class LeadRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, lead_id: UUID) -> Lead | None:
        return await self.session.get(Lead, lead_id)

    async def get_by_idempotency_key(self, key: UUID) -> Lead | None:
        return await self.session.scalar(select(Lead).where(Lead.idempotency_key == key))

    async def create(self, payload: LeadCreate, idempotency_key: UUID) -> Lead:
        lead = Lead(
            name=payload.name,
            email=str(payload.email).lower() if payload.email else None,
            phone=payload.phone,
            original_request=payload.original_request,
            idempotency_key=idempotency_key,
        )
        self.session.add(lead)
        await self.session.commit()
        await self.session.refresh(lead)
        return lead
