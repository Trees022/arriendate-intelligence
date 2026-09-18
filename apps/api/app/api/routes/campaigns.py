from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, status

from app.api.dependencies import SessionDep
from app.api.schemas import (
    CampaignCreate,
    CampaignDetailResponse,
    JobActionRequiredRequest,
    JobFailRequest,
    JobPublishRequest,
    PublicationJobResponse,
    PublicationResponse,
    ReconcileResponse,
)
from app.services.campaigns import CampaignService
from app.services.publication_jobs import PublicationJobService
from app.services.repost import reconcile_cooldowns

router = APIRouter(tags=["campaigns"])


@router.post(
    "/campaigns",
    response_model=CampaignDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_campaign(
    payload: CampaignCreate,
    session: SessionDep,
) -> CampaignDetailResponse:
    service = CampaignService(session)
    return await service.create_campaign(payload)


@router.get(
    "/campaigns/{campaign_id}",
    response_model=CampaignDetailResponse,
)
async def get_campaign(
    campaign_id: UUID,
    session: SessionDep,
) -> CampaignDetailResponse:
    service = CampaignService(session)
    return await service.get_campaign_detail(campaign_id)


@router.get(
    "/properties/{property_id}/campaigns",
    response_model=list[CampaignDetailResponse],
)
async def list_property_campaigns(
    property_id: UUID,
    session: SessionDep,
) -> list[CampaignDetailResponse]:
    service = CampaignService(session)
    return await service.list_by_property(property_id)


@router.post(
    "/campaigns/{campaign_id}/pause",
    response_model=CampaignDetailResponse,
)
async def pause_campaign(
    campaign_id: UUID,
    session: SessionDep,
) -> CampaignDetailResponse:
    service = CampaignService(session)
    return await service.pause_campaign(campaign_id)


@router.post(
    "/campaigns/{campaign_id}/resume",
    response_model=CampaignDetailResponse,
)
async def resume_campaign(
    campaign_id: UUID,
    session: SessionDep,
) -> CampaignDetailResponse:
    service = CampaignService(session)
    return await service.resume_campaign(campaign_id)


@router.post(
    "/publication-jobs/{job_id}/publish",
    response_model=PublicationResponse,
)
async def mark_job_published(
    job_id: UUID,
    payload: JobPublishRequest,
    session: SessionDep,
) -> PublicationResponse:
    service = PublicationJobService(session)
    return await service.mark_published(
        job_id=job_id,
        publication_url=payload.publication_url,
        notes=payload.notes,
    )


@router.post(
    "/publication-jobs/{job_id}/requires-action",
    response_model=PublicationJobResponse,
)
async def mark_job_requires_action(
    job_id: UUID,
    payload: JobActionRequiredRequest,
    session: SessionDep,
) -> PublicationJobResponse:
    return await PublicationJobService(session).mark_action_required(job_id, payload.note)


@router.post(
    "/publication-jobs/{job_id}/fail",
    response_model=PublicationJobResponse,
)
async def mark_job_failed(
    job_id: UUID,
    payload: JobFailRequest,
    session: SessionDep,
) -> PublicationJobResponse:
    return await PublicationJobService(session).mark_failed(
        job_id,
        error_code=payload.error_code,
        error_message=payload.error_message,
    )


@router.post(
    "/publication-jobs/reconcile",
    response_model=ReconcileResponse,
)
async def trigger_reconciliation(
    session: SessionDep,
) -> ReconcileResponse:
    now = datetime.now(UTC)
    count = await reconcile_cooldowns(session, reference_time=now)
    return ReconcileResponse(
        reconciled_jobs=count,
        timestamp=now,
    )
