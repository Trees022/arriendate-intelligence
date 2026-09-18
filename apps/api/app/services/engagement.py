from datetime import UTC
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.db.models import Conversation, Message, Publication, PublicationComment
from app.integrations.contracts import ExternalComment, ExternalMessage


class ExternalEventIngestionService:
    """Idempotently maps provider events into provider-independent domain records."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def ingest_comment(
        self,
        *,
        publication_id: UUID,
        comment: ExternalComment,
        reply_status: str = "new",
        is_demo: bool = False,
    ) -> PublicationComment:
        publication = await self.session.get(Publication, publication_id)
        if not publication:
            raise NotFoundError("Publicación no encontrada")
        existing = await self.session.scalar(
            select(PublicationComment).where(
                PublicationComment.publication_id == publication_id,
                PublicationComment.external_comment_id == comment.external_id,
            )
        )
        if existing:
            return existing
        record = PublicationComment(
            publication_id=publication_id,
            external_comment_id=comment.external_id,
            author_external_id=comment.author_external_id,
            author_display_name=comment.author_display_name,
            body=comment.body[:4000],
            created_external_at=comment.created_at,
            reply_status=reply_status,
            is_demo=is_demo,
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def ingest_message(
        self,
        *,
        conversation_id: UUID,
        message: ExternalMessage,
        direction: str = "inbound",
        is_demo: bool = False,
    ) -> Message:
        conversation = await self.session.get(Conversation, conversation_id)
        if not conversation:
            raise NotFoundError("Conversación no encontrada")
        existing = await self.session.scalar(
            select(Message).where(
                Message.conversation_id == conversation_id,
                Message.external_message_id == message.external_id,
            )
        )
        if existing:
            return existing
        record = Message(
            conversation_id=conversation_id,
            external_message_id=message.external_id,
            direction=direction,
            sender_external_id=message.sender_external_id,
            sender_display_name=message.sender_display_name,
            message_type="text",
            body=message.body[:10000] if message.body else None,
            sent_at=message.sent_at,
            is_demo=is_demo,
        )
        self.session.add(record)
        current_last_message = conversation.last_message_at
        if current_last_message.tzinfo is None:
            current_last_message = current_last_message.replace(tzinfo=UTC)
        sent_at = message.sent_at
        if sent_at.tzinfo is None:
            sent_at = sent_at.replace(tzinfo=UTC)
        conversation.last_message_at = max(current_last_message, sent_at)
        await self.session.commit()
        await self.session.refresh(record)
        return record
