from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Campaign,
    CampaignTarget,
    Publication,
    PublicationJob,
    PublicationPackageVariant,
    PublicationTarget,
)
from app.domain.enums import CampaignStatus, JobStatus


class CampaignRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, campaign_id: UUID) -> Campaign | None:
        return await self.session.get(Campaign, campaign_id)

    async def list_by_property(self, property_id: UUID) -> list[Campaign]:
        rows = await self.session.scalars(
            select(Campaign)
            .where(Campaign.property_id == property_id)
            .order_by(Campaign.created_at.desc())
        )
        return list(rows)

    async def get_targets(self, campaign_id: UUID) -> list[PublicationTarget]:
        rows = await self.session.scalars(
            select(PublicationTarget)
            .join(CampaignTarget, CampaignTarget.target_id == PublicationTarget.id)
            .where(CampaignTarget.campaign_id == campaign_id)
            .order_by(PublicationTarget.name.asc())
        )
        return list(rows)

    async def get_jobs(self, campaign_id: UUID) -> list[PublicationJob]:
        rows = await self.session.scalars(
            select(PublicationJob)
            .where(PublicationJob.campaign_id == campaign_id)
            .order_by(PublicationJob.created_at.asc())
        )
        return list(rows)

    async def get_publications(self, campaign_id: UUID) -> list[Publication]:
        rows = await self.session.scalars(
            select(Publication)
            .where(Publication.campaign_id == campaign_id)
            .order_by(Publication.published_at.desc())
        )
        return list(rows)

    async def get_jobs_by_property(self, property_id: UUID) -> list[PublicationJob]:
        rows = await self.session.scalars(
            select(PublicationJob)
            .where(PublicationJob.property_id == property_id)
            .order_by(PublicationJob.created_at.desc())
        )
        return list(rows)

    async def get_publications_by_property(self, property_id: UUID) -> list[Publication]:
        rows = await self.session.scalars(
            select(Publication)
            .where(Publication.property_id == property_id)
            .order_by(Publication.published_at.desc())
        )
        return list(rows)

    async def get_job(self, job_id: UUID) -> PublicationJob | None:
        return await self.session.get(PublicationJob, job_id)

    async def create_campaign_with_jobs(
        self,
        *,
        property_id: UUID,
        package_id: UUID,
        targets: list[PublicationTarget],
        variants: list[PublicationPackageVariant],
    ) -> Campaign:
        # Variant lookup map by channel_type
        variant_channels = {v.channel_type for v in variants}

        campaign = Campaign(
            property_id=property_id,
            package_id=package_id,
            status=CampaignStatus.ACTIVE.value,
        )
        self.session.add(campaign)
        await self.session.flush()

        for target in targets:
            campaign_target = CampaignTarget(
                campaign_id=campaign.id,
                target_id=target.id,
            )
            self.session.add(campaign_target)
            await self.session.flush()

            if target.channel_type not in variant_channels:
                raise ValueError(
                    f"El paquete no tiene variante para el canal {target.channel_type}"
                )

            job = PublicationJob(
                campaign_id=campaign.id,
                campaign_target_id=campaign_target.id,
                property_id=property_id,
                target_id=target.id,
                package_id=package_id,
                variant_type=target.channel_type,
                execution_mode=target.execution_mode,
                status=JobStatus.READY.value,
                attempt_count=0,
            )
            self.session.add(job)

        await self.session.commit()
        await self.session.refresh(campaign)
        return campaign

    async def update_status(
        self, campaign: Campaign, new_status: CampaignStatus
    ) -> Campaign:
        campaign.status = new_status.value
        await self.session.commit()
        await self.session.refresh(campaign)
        return campaign

    async def record_publication(
        self,
        *,
        job: PublicationJob,
        publication_url: str | None,
        channel_account_id: UUID | None,
        external_publication_id: str | None = None,
        published_at: datetime | None = None,
    ) -> Publication:
        pub_at = published_at or datetime.now(UTC)
        pub = Publication(
            job_id=job.id,
            property_id=job.property_id,
            campaign_id=job.campaign_id,
            target_id=job.target_id,
            package_id=job.package_id,
            channel_account_id=channel_account_id,
            variant_type=job.variant_type,
            external_publication_id=external_publication_id,
            published_at=pub_at,
            publication_url=publication_url,
            execution_mode=job.execution_mode,
        )
        self.session.add(pub)
        await self.session.flush()
        return pub

    async def get_cooldown_jobs_eligible(
        self, reference_time: datetime
    ) -> list[PublicationJob]:
        rows = await self.session.scalars(
            select(PublicationJob)
            .where(
                PublicationJob.status == JobStatus.COOLDOWN.value,
                PublicationJob.next_eligible_at <= reference_time,
            )
        )
        return list(rows)
