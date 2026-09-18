from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import PublicationTargetCreate
from app.core.errors import NotFoundError, ValidationError
from app.db.models import ChannelAccount, PublicationTarget
from app.domain.enums import ChannelType
from app.repositories.publication_targets import PublicationTargetRepository


class PublicationTargetService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = PublicationTargetRepository(session)

    async def list(
        self, *, active_only: bool = False
    ) -> list[PublicationTarget]:
        return await self.repository.list(active_only=active_only)

    async def get(self, target_id: UUID) -> PublicationTarget:
        target = await self.repository.get(target_id)
        if not target:
            raise NotFoundError("Destino de publicación no encontrado")
        return target

    async def create(self, payload: PublicationTargetCreate) -> PublicationTarget:
        if payload.channel_account_id:
            account = await self.session.get(ChannelAccount, payload.channel_account_id)
            if not account:
                raise NotFoundError("Cuenta de canal no encontrada")
            expected_account_type = {
                ChannelType.FACEBOOK_PAGE: "facebook_page",
                ChannelType.INSTAGRAM_PROFESSIONAL: "instagram_professional",
            }.get(payload.channel_type)
            if expected_account_type != account.account_type:
                raise ValidationError(
                    "La cuenta conectada no corresponde al canal del destino"
                )
        record: dict[str, object] = {
            "name": payload.name,
            "channel_type": payload.channel_type.value,
            "execution_mode": payload.execution_mode.value,
            "channel_account_id": payload.channel_account_id,
            "destination_url": payload.destination_url,
            "geographic_relevance": payload.geographic_relevance,
            "property_tags": payload.property_tags,
            "active": payload.active,
            "minimum_repost_interval_hours": payload.minimum_repost_interval_hours,
            "notes": payload.notes,
            "is_demo": False,
        }
        return await self.repository.create(record)
