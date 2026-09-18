from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest

from app.db.models import Conversation, Publication
from app.db.seed import seed_demo_properties
from app.db.session import Database
from app.integrations.contracts import ExternalComment, ExternalMessage
from app.services.engagement import ExternalEventIngestionService


@pytest.mark.asyncio
async def test_comment_and_message_ingestion_is_idempotent_with_scoped_external_ids(
    tmp_path: Path,
) -> None:
    database = Database(f"sqlite+aiosqlite:///{(tmp_path / 'events.db').as_posix()}")
    await database.initialize_local_schema()
    try:
        async with database.session() as session:
            await seed_demo_properties(session)
            publication = await session.get(
                Publication, UUID("60000000-0000-4000-8000-000000000001")
            )
            conversation = await session.get(
                Conversation, UUID("80000000-0000-4000-8000-000000000001")
            )
            assert publication is not None
            assert conversation is not None
            service = ExternalEventIngestionService(session)
            comment = ExternalComment(
                external_id="fixture-idempotent-comment",
                author_external_id=None,
                author_display_name="Demo",
                body="Comentario repetido",
                created_at=datetime(2026, 9, 18, tzinfo=UTC),
            )
            first_comment = await service.ingest_comment(
                publication_id=publication.id,
                comment=comment,
                is_demo=True,
            )
            second_comment = await service.ingest_comment(
                publication_id=publication.id,
                comment=comment,
                is_demo=True,
            )
            assert first_comment.id == second_comment.id

            message = ExternalMessage(
                external_id="fixture-idempotent-message",
                conversation_external_id=conversation.external_conversation_id,
                sender_external_id=None,
                sender_display_name="Demo",
                body="Mensaje repetido",
                sent_at=datetime(2026, 9, 18, tzinfo=UTC),
            )
            first_message = await service.ingest_message(
                conversation_id=conversation.id,
                message=message,
                is_demo=True,
            )
            second_message = await service.ingest_message(
                conversation_id=conversation.id,
                message=message,
                is_demo=True,
            )
            assert first_message.id == second_message.id
    finally:
        await database.dispose()
