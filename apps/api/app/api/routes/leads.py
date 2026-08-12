from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, Query, status

from app.api.dependencies import EmbeddingProviderDep, GeneratorDep, SessionDep, SettingsDep
from app.api.schemas import (
    AIRunResponse,
    ConstraintCheckResponse,
    ExclusionSummaryResponse,
    LeadCreate,
    LeadDetailResponse,
    LeadExtractionResponse,
    LeadMatchesResponse,
    LeadRequirementsResponse,
    LeadResponse,
    PropertyMatchResponse,
    PropertyResponse,
    SoftMatchReasonResponse,
)
from app.domain.enums import LeadStatus
from app.services.extractions import LeadExtractionService
from app.services.leads import LeadService
from app.services.matching import MatchingView, PropertyMatchingService

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


def matching_response(result: MatchingView) -> LeadMatchesResponse:
    run = result.run
    items = result.items
    if run is None:
        return LeadMatchesResponse(
            status="not_run",
            run_id=None,
            algorithm_version=None,
            embedding_provider=None,
            embedding_model=None,
            requested_top_k=None,
            total_properties=0,
            candidate_count=0,
            result_count=0,
            latency_ms=None,
            embedding_latency_ms=None,
            exclusion_summary=[],
            items=[],
            created_at=None,
        )
    return LeadMatchesResponse(
        status="succeeded",
        run_id=run.id,
        algorithm_version=run.algorithm_version,
        embedding_provider=run.provider,
        embedding_model=run.model,
        requested_top_k=run.requested_top_k,
        total_properties=run.total_properties,
        candidate_count=run.candidate_count,
        result_count=run.result_count,
        latency_ms=run.latency_ms,
        embedding_latency_ms=run.embedding_latency_ms,
        exclusion_summary=[
            ExclusionSummaryResponse.model_validate(item) for item in run.exclusion_summary
        ],
        items=[
            PropertyMatchResponse(
                rank=item.match.rank,
                semantic_score=(
                    float(item.match.semantic_score)
                    if item.match.semantic_score is not None
                    else None
                ),
                hard_constraint_matches=[
                    ConstraintCheckResponse.model_validate(check)
                    for check in item.match.hard_constraint_matches
                ],
                soft_match_reasons=[
                    SoftMatchReasonResponse.model_validate(reason)
                    for reason in item.match.soft_match_reasons
                ],
                property=PropertyResponse.model_validate(item.property),
            )
            for item in items
        ],
        created_at=run.created_at,
    )


@router.post("/{lead_id}/matches", response_model=LeadMatchesResponse)
async def match_lead(
    lead_id: UUID,
    session: SessionDep,
    embedding_provider: EmbeddingProviderDep,
    top_k: int = Query(default=3, ge=1, le=10),
) -> LeadMatchesResponse:
    result = await PropertyMatchingService(session, embedding_provider).match(
        lead_id, top_k=top_k
    )
    return matching_response(result)


@router.get("/{lead_id}/matches", response_model=LeadMatchesResponse)
async def get_lead_matches(
    lead_id: UUID,
    session: SessionDep,
    embedding_provider: EmbeddingProviderDep,
) -> LeadMatchesResponse:
    result = await PropertyMatchingService(session, embedding_provider).get_latest(lead_id)
    return matching_response(result)
