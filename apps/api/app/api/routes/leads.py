from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, status

from app.api.dependencies import SessionDep
from app.api.schemas import LeadCreate, LeadResponse
from app.services.leads import LeadService

router = APIRouter(prefix="/leads", tags=["leads"])


@router.post("", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
async def create_lead(
    payload: LeadCreate,
    idempotency_key: Annotated[UUID, Header(alias="Idempotency-Key")],
    session: SessionDep,
) -> LeadResponse:
    lead = await LeadService(session).create(payload, idempotency_key)
    return LeadResponse.model_validate(lead)


@router.get("/{lead_id}", response_model=LeadResponse)
async def get_lead(
    lead_id: UUID,
    session: SessionDep,
) -> LeadResponse:
    lead = await LeadService(session).get(lead_id)
    return LeadResponse.model_validate(lead)
