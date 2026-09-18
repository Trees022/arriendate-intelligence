from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Campaign,
    ChannelAccount,
    Conversation,
    EngagementSnapshot,
    Message,
    Publication,
    PublicationComment,
    PublicationPackageVariant,
)


class CommandCenterRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_channel_accounts(self) -> list[ChannelAccount]:
        rows = await self.session.scalars(
            select(ChannelAccount).order_by(ChannelAccount.display_name.asc())
        )
        return list(rows)

    async def get_variant(
        self, package_id: UUID, channel_type: str
    ) -> PublicationPackageVariant | None:
        return cast(
            PublicationPackageVariant | None,
            await self.session.scalar(
                select(PublicationPackageVariant).where(
                    PublicationPackageVariant.package_id == package_id,
                    PublicationPackageVariant.channel_type == channel_type,
                )
            ),
        )

    async def list_snapshots(self, property_id: UUID) -> list[EngagementSnapshot]:
        rows = await self.session.scalars(
            select(EngagementSnapshot)
            .join(Publication, Publication.id == EngagementSnapshot.publication_id)
            .where(Publication.property_id == property_id)
            .order_by(EngagementSnapshot.captured_at.desc())
        )
        return list(rows)

    async def list_comments(self, property_id: UUID) -> list[PublicationComment]:
        rows = await self.session.scalars(
            select(PublicationComment)
            .join(Publication, Publication.id == PublicationComment.publication_id)
            .where(Publication.property_id == property_id)
            .order_by(PublicationComment.created_external_at.desc())
            .limit(30)
        )
        return list(rows)

    async def list_conversations(self, property_id: UUID) -> list[Conversation]:
        rows = await self.session.scalars(
            select(Conversation)
            .where(Conversation.property_id == property_id)
            .order_by(Conversation.last_message_at.desc())
        )
        return list(rows)

    async def list_messages(self, conversation_id: UUID) -> list[Message]:
        rows = await self.session.scalars(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.sent_at.asc())
        )
        return list(rows)

    async def list_campaigns(self, property_id: UUID) -> list[Campaign]:
        rows = await self.session.scalars(
            select(Campaign)
            .where(Campaign.property_id == property_id)
            .order_by(Campaign.created_at.desc())
        )
        return list(rows)
