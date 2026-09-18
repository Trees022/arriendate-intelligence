from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import (
    CampaignDetailResponse,
    CapabilityStatusResponse,
    ChannelAccountResponse,
    ConversationResponse,
    DistributionItemResponse,
    EngagementSnapshotResponse,
    EngagementSummaryResponse,
    MessageResponse,
    PropertyCommandCenterResponse,
    PropertyMediaResponse,
    PropertyResponse,
    PublicationCommentResponse,
    PublicationJobResponse,
    PublicationPackageVariantResponse,
    PublicationResponse,
    PublicationTargetResponse,
)
from app.core.errors import NotFoundError
from app.db.models import EngagementSnapshot, Publication, PublicationJob
from app.domain.capabilities import capabilities_for_account, capabilities_for_target
from app.domain.enums import (
    AccountType,
    ChannelType,
    ConnectionStatus,
    ConversationStatus,
    JobStatus,
)
from app.repositories.campaigns import CampaignRepository
from app.repositories.command_center import CommandCenterRepository
from app.repositories.media import PropertyMediaRepository
from app.repositories.properties import PropertyRepository
from app.repositories.publication_packages import PublicationPackageRepository
from app.repositories.publication_targets import PublicationTargetRepository
from app.services.campaigns import CampaignService
from app.services.property_actions import compute_property_actions
from app.services.publication_packages import compute_property_fingerprint
from app.storage.contracts import PropertyMediaStorage


class PropertyCommandCenterService:
    def __init__(
        self,
        session: AsyncSession,
        storage: PropertyMediaStorage,
    ) -> None:
        self.session = session
        self.storage = storage
        self.repository = CommandCenterRepository(session)
        self.property_repository = PropertyRepository(session)
        self.target_repository = PublicationTargetRepository(session)
        self.campaign_repository = CampaignRepository(session)
        self.package_repository = PublicationPackageRepository(session)
        self.media_repository = PropertyMediaRepository(session)

    async def get(self, property_id: UUID) -> PropertyCommandCenterResponse:
        prop = await self.property_repository.get(property_id)
        if not prop:
            raise NotFoundError("Propiedad no encontrada")

        accounts = await self.repository.list_channel_accounts()
        account_by_id = {account.id: account for account in accounts}
        targets = await self.target_repository.list(active_only=True)
        jobs = await self.campaign_repository.get_jobs_by_property(property_id)
        publications = await self.campaign_repository.get_publications_by_property(property_id)
        snapshots = await self.repository.list_snapshots(property_id)
        comments = await self.repository.list_comments(property_id)
        conversations = await self.repository.list_conversations(property_id)
        campaigns = await self.repository.list_campaigns(property_id)
        media = await self.media_repository.list_by_property(property_id)
        packages = await self.package_repository.list_by_property(property_id)

        latest_job_by_target: dict[UUID, PublicationJob] = {}
        for existing_job in jobs:
            latest_job_by_target.setdefault(existing_job.target_id, existing_job)
        latest_publication_by_target: dict[UUID, Publication] = {}
        for existing_publication in publications:
            latest_publication_by_target.setdefault(
                existing_publication.target_id, existing_publication
            )

        media_responses = {
            item.id: PropertyMediaResponse(
                id=item.id,
                property_id=item.property_id,
                storage_key=item.storage_key,
                original_filename=item.original_filename,
                media_type=item.media_type,
                mime_type=item.mime_type,
                size_bytes=item.size_bytes,
                position=item.position,
                is_cover=item.is_cover,
                url=self.storage.get_url(item.storage_key),
                created_at=item.created_at,
            )
            for item in media
        }

        distribution: list[DistributionItemResponse] = []
        for target in targets:
            job = latest_job_by_target.get(target.id)
            publication = latest_publication_by_target.get(target.id)
            variant = (
                await self.repository.get_variant(job.package_id, job.variant_type)
                if job
                else None
            )
            account = (
                account_by_id.get(target.channel_account_id)
                if target.channel_account_id
                else None
            )
            capability_items = (
                capabilities_for_account(
                    AccountType(account.account_type),
                    ConnectionStatus(account.connection_status),
                )
                if account
                else capabilities_for_target(ChannelType(target.channel_type))
            )
            prepared_media = []
            if variant:
                prepared_media = [
                    media_responses[media_id]
                    for media_id in variant.suggested_media_ids
                    if media_id in media_responses
                ]
            distribution.append(
                DistributionItemResponse(
                    target=PublicationTargetResponse.model_validate(target),
                    job=PublicationJobResponse.model_validate(job) if job else None,
                    latest_publication=(
                        PublicationResponse.model_validate(publication) if publication else None
                    ),
                    package_variant=(
                        PublicationPackageVariantResponse.model_validate(variant)
                        if variant
                        else None
                    ),
                    prepared_media=prepared_media,
                    status=self._distribution_status(job, publication is not None),
                    last_publication_at=publication.published_at if publication else None,
                    next_eligible_at=job.next_eligible_at if job else None,
                    publication_url=publication.publication_url if publication else None,
                    action_required=job.action_required if job else False,
                    capabilities=[
                        CapabilityStatusResponse(
                            capability=item.capability,
                            availability=item.availability,
                            reason=item.reason,
                        )
                        for item in capability_items
                    ],
                )
            )

        conversation_responses: list[ConversationResponse] = []
        for conversation in conversations:
            messages = await self.repository.list_messages(conversation.id)
            conversation_responses.append(
                ConversationResponse(
                    id=conversation.id,
                    channel_account_id=conversation.channel_account_id,
                    external_conversation_id=conversation.external_conversation_id,
                    channel_type=ChannelType(conversation.channel_type),
                    property_id=conversation.property_id,
                    publication_id=conversation.publication_id,
                    lead_id=conversation.lead_id,
                    status=ConversationStatus(conversation.status),
                    last_message_at=conversation.last_message_at,
                    is_demo=conversation.is_demo,
                    messages=[MessageResponse.model_validate(message) for message in messages],
                )
            )

        fingerprint = compute_property_fingerprint(prop, media)
        package_is_stale = any(
            package.status == "approved" and package.property_fingerprint != fingerprint
            for package in packages
        )
        actions = compute_property_actions(
            prop=prop,
            targets=targets,
            jobs=jobs,
            publications=publications,
            conversations=conversations,
            comments=comments,
            campaigns=campaigns,
            package_is_stale=package_is_stale,
            media_count=len(media),
        )

        campaign_details: list[CampaignDetailResponse] = await CampaignService(
            self.session
        ).list_by_property(property_id)
        return PropertyCommandCenterResponse(
            property=PropertyResponse.model_validate(prop),
            demo_mode=any(account.is_demo for account in accounts)
            or any(target.is_demo for target in targets),
            channel_accounts=[
                ChannelAccountResponse.model_validate(account) for account in accounts
            ],
            distribution=distribution,
            engagement=self._summarize_engagement(snapshots),
            engagement_snapshots=[
                EngagementSnapshotResponse.model_validate(snapshot) for snapshot in snapshots
            ],
            recent_comments=[
                PublicationCommentResponse.model_validate(comment) for comment in comments
            ],
            related_conversations=conversation_responses,
            next_actions=actions,
            campaigns=campaign_details,
        )

    @staticmethod
    def _distribution_status(job: PublicationJob | None, has_publication: bool) -> str:
        if job is None:
            return "not_scheduled"
        if job.action_required:
            return "requires_action"
        if job.status == JobStatus.COOLDOWN.value:
            return "cooldown"
        if job.status == JobStatus.READY.value and has_publication:
            return "ready_to_repost"
        if job.status == JobStatus.READY.value:
            return "ready"
        return job.status

    @staticmethod
    def _summarize_engagement(
        snapshots: list[EngagementSnapshot],
    ) -> EngagementSummaryResponse:
        latest_by_publication: dict[UUID, EngagementSnapshot] = {}
        for snapshot in snapshots:
            latest_by_publication.setdefault(snapshot.publication_id, snapshot)
        latest = list(latest_by_publication.values())

        def total(attribute: str) -> int | None:
            values = [getattr(snapshot, attribute) for snapshot in latest]
            known = [value for value in values if value is not None]
            return sum(known) if known else None

        return EngagementSummaryResponse(
            comments_count=total("comments_count"),
            reactions_count=total("reactions_count"),
            views_count=total("views_count"),
            impressions_count=total("impressions_count"),
            messages_count=total("messages_count"),
            last_captured_at=max(
                (snapshot.captured_at for snapshot in snapshots), default=None
            ),
        )
