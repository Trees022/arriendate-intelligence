from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, status

from app.api.dependencies import GeneratorDep, SessionDep, SettingsDep
from app.api.schemas import (
    AIRunResponse,
    LeadCreate,
    LeadDetailResponse,
    LeadExtractionResponse,
    LeadRequirementsResponse,
    LeadResponse,
)
from app.domain.enums import LeadStatus
from app.services.extractions import LeadExtractionService
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


@router.get("/{lead_id}", response_model=LeadDetailResponse)
async def get_lead(
    lead_id: UUID,
    session: SessionDep,
) -> LeadDetailResponse:
    detail = await LeadService(session).get_detail(lead_id)
    lead = LeadResponse.model_validate(detail.lead)
    return LeadDetailResponse(
        **lead.model_dump(),
        requirements=(
            LeadRequirementsResponse.model_validate(detail.requirements)
            if detail.requirements
            else None
        ),
        ai_runs=[AIRunResponse.model_validate(run) for run in detail.ai_runs],
    )


@router.post("/{lead_id}/extract", response_model=LeadExtractionResponse)
async def extract_lead(
    lead_id: UUID,
    session: SessionDep,
    generator: GeneratorDep,
    settings: SettingsDep,
) -> LeadExtractionResponse:
    result = await LeadExtractionService(session, generator, settings).extract(lead_id)
    return LeadExtractionResponse(
        lead_status=LeadStatus(result.lead.status),
        requirements=LeadRequirementsResponse.model_validate(result.requirements),
        ai_run=AIRunResponse.model_validate(result.run),
    )
