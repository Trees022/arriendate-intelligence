from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import PublicationJobResponse, PublicationResponse
from app.core.errors import NotFoundError, ValidationError
from app.db.models import PublicationJob
from app.domain.enums import (
    CampaignStatus,
    ChannelType,
    CommercialStatus,
    ExecutionMode,
    JobStatus,
)
from app.repositories.campaigns import CampaignRepository
from app.repositories.properties import PropertyRepository
from app.repositories.publication_targets import PublicationTargetRepository


class PublicationJobService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.campaign_repository = CampaignRepository(session)
        self.property_repository = PropertyRepository(session)
        self.target_repository = PublicationTargetRepository(session)

    async def mark_published(
        self,
        *,
        job_id: UUID,
        publication_url: str | None = None,
        notes: str | None = None,
        published_at: datetime | None = None,
    ) -> PublicationResponse:
        job = await self.campaign_repository.get_job(job_id)
        if not job:
            raise NotFoundError("Trabajo de publicación no encontrado")

        if job.status not in (
            JobStatus.READY.value,
            JobStatus.RUNNING.value,
            JobStatus.PENDING.value,
            JobStatus.FAILED.value,
        ):
            raise ValidationError(
                f"No se puede publicar un trabajo en estado '{job.status}'"
            )

        campaign = await self.campaign_repository.get(job.campaign_id)
        if not campaign or campaign.status != CampaignStatus.ACTIVE.value:
            raise ValidationError("La campaña debe estar activa para registrar la publicación")
        prop = await self.property_repository.get(job.property_id)
        if not prop or prop.commercial_status != CommercialStatus.ACTIVE.value:
            raise ValidationError("La propiedad debe estar activa para publicar")

        target = await self.target_repository.get(job.target_id)
        if not target:
            raise NotFoundError("Destino no encontrado")

        pub_time = published_at or datetime.now(UTC)

        # Calculate cooldown and next eligible time
        if target.minimum_repost_interval_hours > 0:
            job.status = JobStatus.COOLDOWN.value
            job.next_eligible_at = pub_time + timedelta(
                hours=target.minimum_repost_interval_hours
            )
        else:
            job.status = JobStatus.READY.value
            job.next_eligible_at = None

        job.attempt_count += 1
        job.error_code = None
        job.error_message = None
        job.action_required = False
        job.action_note = notes

        publication = await self.campaign_repository.record_publication(
            job=job,
            publication_url=publication_url,
            channel_account_id=target.channel_account_id,
            published_at=pub_time,
        )

        await self.session.commit()
        await self.session.refresh(job)

        return PublicationResponse(
            id=publication.id,
            job_id=publication.job_id,
            property_id=publication.property_id,
            campaign_id=publication.campaign_id,
            target_id=publication.target_id,
            package_id=publication.package_id,
            channel_account_id=publication.channel_account_id,
            variant_type=ChannelType(publication.variant_type),
            external_publication_id=publication.external_publication_id,
            published_at=publication.published_at,
            publication_url=publication.publication_url,
            execution_mode=ExecutionMode(publication.execution_mode),
            created_at=publication.created_at,
        )

    async def mark_action_required(
        self, job_id: UUID, note: str
    ) -> PublicationJobResponse:
        job = await self._get_job(job_id)
        if job.status in {JobStatus.CANCELLED.value, JobStatus.PUBLISHED.value}:
            raise ValidationError(
                f"No se puede solicitar acción para un trabajo en estado '{job.status}'"
            )
        job.action_required = True
        job.action_note = note
        await self.session.commit()
        await self.session.refresh(job)
        return self._to_job_response(job)

    async def mark_failed(
        self, job_id: UUID, *, error_code: str, error_message: str
    ) -> PublicationJobResponse:
        job = await self._get_job(job_id)
        if job.status == JobStatus.CANCELLED.value:
            raise ValidationError("No se puede fallar un trabajo cancelado")
        job.status = JobStatus.FAILED.value
        job.error_code = error_code
        job.error_message = error_message
        job.action_required = True
        job.action_note = "Revisar el error antes de volver a intentar."
        job.attempt_count += 1
        await self.session.commit()
        await self.session.refresh(job)
        return self._to_job_response(job)

    async def _get_job(self, job_id: UUID) -> PublicationJob:
        job = await self.campaign_repository.get_job(job_id)
        if not job:
            raise NotFoundError("Trabajo de publicación no encontrado")
        return job

    @staticmethod
    def _to_job_response(job: PublicationJob) -> PublicationJobResponse:
        return PublicationJobResponse(
            id=job.id,
            campaign_id=job.campaign_id,
            campaign_target_id=job.campaign_target_id,
            property_id=job.property_id,
            target_id=job.target_id,
            package_id=job.package_id,
            variant_type=ChannelType(job.variant_type),
            execution_mode=ExecutionMode(job.execution_mode),
            status=JobStatus(job.status),
            scheduled_at=job.scheduled_at,
            next_eligible_at=job.next_eligible_at,
            attempt_count=job.attempt_count,
            error_code=job.error_code,
            error_message=job.error_message,
            action_required=job.action_required,
            action_note=job.action_note,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )
