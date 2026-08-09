from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import LeadCreate
from app.core.errors import ConflictError, NotFoundError
from app.db.models import Lead
from app.repositories.leads import LeadRepository


class LeadService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = LeadRepository(session)

    async def create(self, payload: LeadCreate, idempotency_key: UUID) -> Lead:
        existing = await self.repository.get_by_idempotency_key(idempotency_key)
        if existing:
            same_request = (
                existing.original_request == payload.original_request
                and existing.name == payload.name
                and existing.email == (str(payload.email).lower() if payload.email else None)
                and existing.phone == payload.phone
            )
            if not same_request:
                raise ConflictError("La clave de idempotencia ya fue usada con otra solicitud")
            return existing
        return await self.repository.create(payload, idempotency_key)

    async def get(self, lead_id: UUID) -> Lead:
        lead = await self.repository.get(lead_id)
        if not lead:
            raise NotFoundError("Lead no encontrado")
        return lead
