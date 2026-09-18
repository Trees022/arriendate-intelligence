from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import (
    CampaignCreate,
    CampaignDetailResponse,
    PublicationJobResponse,
    PublicationResponse,
    PublicationTargetResponse,
)
from app.core.errors import NotFoundError, ValidationError
from app.db.models import Campaign, Publication, PublicationJob, PublicationTarget
from app.domain.enums import (
    CampaignStatus,
    ChannelType,
    CommercialStatus,
    ExecutionMode,
    JobStatus,
    PackageStatus,
)
from app.repositories.campaigns import CampaignRepository
from app.repositories.properties import PropertyRepository
from app.repositories.publication_packages import PublicationPackageRepository
from app.repositories.publication_targets import PublicationTargetRepository


class CampaignService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = CampaignRepository(session)
        self.property_repository = PropertyRepository(session)
        self.package_repository = PublicationPackageRepository(session)
        self.target_repository = PublicationTargetRepository(session)

    async def create_campaign(
        self, payload: CampaignCreate
    ) -> CampaignDetailResponse:
        prop = await self.property_repository.get(payload.property_id)
        if not prop:
            raise NotFoundError("Propiedad no encontrada")

        if prop.commercial_status != CommercialStatus.ACTIVE.value:
            raise ValidationError(
                "La propiedad debe estar activa antes de crear una campaña"
            )

        package = await self.package_repository.get(payload.package_id)
        if not package:
            raise NotFoundError("Paquete de publicación no encontrado")

        if package.status != PackageStatus.APPROVED.value:
            raise ValidationError(
                "El paquete de publicación debe estar aprobado para poder lanzar una campaña"
            )
        if package.property_id != payload.property_id:
            raise ValidationError(
                "El paquete de publicación no pertenece a la propiedad seleccionada"
            )

        targets: list[PublicationTarget] = []
        for tid in payload.target_ids:
            target = await self.target_repository.get(tid)
            if not target:
                raise NotFoundError(f"Destino de publicación {tid} no encontrado")
            if not target.active:
                raise ValidationError(f"El destino '{target.name}' no está activo")
            targets.append(target)

        variants = await self.package_repository.list_variants(package.id)
        variant_channels = {variant.channel_type for variant in variants}
        missing_channels = sorted(
            {target.channel_type for target in targets} - variant_channels
        )
        if missing_channels:
            raise ValidationError(
                "El paquete no contiene variantes para: " + ", ".join(missing_channels)
            )

        campaign = await self.repository.create_campaign_with_jobs(
            property_id=payload.property_id,
            package_id=payload.package_id,
            targets=targets,
            variants=variants,
        )
        return await self.get_campaign_detail(campaign.id)

    async def get_campaign_detail(
        self, campaign_id: UUID
    ) -> CampaignDetailResponse:
        campaign = await self.repository.get(campaign_id)
        if not campaign:
            raise NotFoundError("Campaña no encontrada")

        targets = await self.repository.get_targets(campaign_id)
        jobs = await self.repository.get_jobs(campaign_id)
        publications = await self.repository.get_publications(campaign_id)

        return self._to_detail_response(campaign, targets, jobs, publications)

    async def list_by_property(
        self, property_id: UUID
    ) -> list[CampaignDetailResponse]:
        campaigns = await self.repository.list_by_property(property_id)
        details: list[CampaignDetailResponse] = []
        for c in campaigns:
            targets = await self.repository.get_targets(c.id)
            jobs = await self.repository.get_jobs(c.id)
            publications = await self.repository.get_publications(c.id)
            details.append(self._to_detail_response(c, targets, jobs, publications))
        return details

    async def pause_campaign(self, campaign_id: UUID) -> CampaignDetailResponse:
        campaign = await self.repository.get(campaign_id)
        if not campaign:
            raise NotFoundError("Campaña no encontrada")
        if campaign.status != CampaignStatus.ACTIVE.value:
            raise ValidationError("Sólo una campaña activa puede pausarse")
        await self.repository.update_status(campaign, CampaignStatus.PAUSED)
        return await self.get_campaign_detail(campaign_id)

    async def resume_campaign(self, campaign_id: UUID) -> CampaignDetailResponse:
        campaign = await self.repository.get(campaign_id)
        if not campaign:
            raise NotFoundError("Campaña no encontrada")
        if campaign.status != CampaignStatus.PAUSED.value:
            raise ValidationError("Sólo una campaña pausada puede reanudarse")
        prop = await self.property_repository.get(campaign.property_id)
        if not prop or prop.commercial_status != CommercialStatus.ACTIVE.value:
            raise ValidationError("La propiedad debe estar activa para reanudar la campaña")
        await self.repository.update_status(campaign, CampaignStatus.ACTIVE)
        return await self.get_campaign_detail(campaign_id)

    def _to_detail_response(
        self,
        campaign: Campaign,
        targets: list[PublicationTarget],
        jobs: list[PublicationJob],
        publications: list[Publication],
    ) -> CampaignDetailResponse:
        return CampaignDetailResponse(
            id=campaign.id,
            property_id=campaign.property_id,
            package_id=campaign.package_id,
            status=CampaignStatus(campaign.status),
            targets=[
                PublicationTargetResponse(
                    id=t.id,
                    name=t.name,
                    channel_type=ChannelType(t.channel_type),
                    execution_mode=ExecutionMode(t.execution_mode),
                    channel_account_id=t.channel_account_id,
                    destination_url=t.destination_url,
                    geographic_relevance=t.geographic_relevance,
                    property_tags=t.property_tags,
                    active=t.active,
                    minimum_repost_interval_hours=t.minimum_repost_interval_hours,
                    notes=t.notes,
                    is_demo=t.is_demo,
                    created_at=t.created_at,
                    updated_at=t.updated_at,
                )
                for t in targets
            ],
            jobs=[
                PublicationJobResponse(
                    id=j.id,
                    campaign_id=j.campaign_id,
                    campaign_target_id=j.campaign_target_id,
                    property_id=j.property_id,
                    target_id=j.target_id,
                    package_id=j.package_id,
                    variant_type=ChannelType(j.variant_type),
                    execution_mode=ExecutionMode(j.execution_mode),
                    status=JobStatus(j.status),
                    scheduled_at=j.scheduled_at,
                    next_eligible_at=j.next_eligible_at,
                    attempt_count=j.attempt_count,
                    error_code=j.error_code,
                    error_message=j.error_message,
                    action_required=j.action_required,
                    action_note=j.action_note,
                    created_at=j.created_at,
                    updated_at=j.updated_at,
                )
                for j in jobs
            ],
            publications=[
                PublicationResponse(
                    id=p.id,
                    job_id=p.job_id,
                    property_id=p.property_id,
                    campaign_id=p.campaign_id,
                    target_id=p.target_id,
                    package_id=p.package_id,
                    channel_account_id=p.channel_account_id,
                    variant_type=ChannelType(p.variant_type),
                    external_publication_id=p.external_publication_id,
                    published_at=p.published_at,
                    publication_url=p.publication_url,
                    execution_mode=ExecutionMode(p.execution_mode),
                    created_at=p.created_at,
                )
                for p in publications
            ],
            created_at=campaign.created_at,
            updated_at=campaign.updated_at,
        )
