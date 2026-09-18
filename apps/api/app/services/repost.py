from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import CampaignStatus, CommercialStatus, JobStatus
from app.repositories.campaigns import CampaignRepository
from app.repositories.properties import PropertyRepository


async def reconcile_cooldowns(
    session: AsyncSession, reference_time: datetime | None = None
) -> int:
    """Deterministic, idempotent reconciler for expired cooldown jobs."""
    now = reference_time or datetime.now(UTC)
    campaign_repo = CampaignRepository(session)
    property_repo = PropertyRepository(session)

    eligible_jobs = await campaign_repo.get_cooldown_jobs_eligible(now)
    reconciled_count = 0

    for job in eligible_jobs:
        prop = await property_repo.get(job.property_id)
        campaign = await campaign_repo.get(job.campaign_id)

        # If property is closed/archived/reserved, cancel future runs
        if prop and prop.commercial_status in (
            CommercialStatus.CLOSED.value,
            CommercialStatus.ARCHIVED.value,
            CommercialStatus.RESERVED.value,
        ):
            job.status = JobStatus.CANCELLED.value
            reconciled_count += 1
        elif campaign and campaign.status == CampaignStatus.ACTIVE.value:
            # Active campaign and available property -> ready for next repost
            job.status = JobStatus.READY.value
            reconciled_count += 1
        # If campaign is paused, job stays in cooldown until resumed/re-evaluated

    if reconciled_count > 0:
        await session.commit()

    return reconciled_count
