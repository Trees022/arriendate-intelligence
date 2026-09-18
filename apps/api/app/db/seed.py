from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.properties import DEMO_PROPERTIES
from app.db.models import (
    Campaign,
    CampaignTarget,
    ChannelAccount,
    Conversation,
    EngagementSnapshot,
    Message,
    Property,
    Publication,
    PublicationComment,
    PublicationJob,
    PublicationPackage,
    PublicationPackageVariant,
    PublicationTarget,
)
from app.domain.capabilities import capabilities_for_account
from app.domain.enums import AccountType, ConnectionStatus
from app.services.publication_packages import compute_property_fingerprint

DEMO_PAGE_ACCOUNT_ID = UUID("20000000-0000-4000-8000-000000000001")
DEMO_INSTAGRAM_ACCOUNT_ID = UUID("20000000-0000-4000-8000-000000000002")
DEMO_PACKAGE_ID = UUID("30000000-0000-4000-8000-000000000001")
DEMO_CAMPAIGN_ID = UUID("40000000-0000-4000-8000-000000000001")


def _capability_map(account_type: AccountType) -> dict[str, str]:
    return {
        item.capability.value: item.availability.value
        for item in capabilities_for_account(account_type, ConnectionStatus.FIXTURE)
    }


async def seed_demo_properties(session: AsyncSession) -> int:
    """Insert deterministic synthetic inventory into an empty property table."""
    count = await session.scalar(select(func.count()).select_from(Property))
    inserted = 0
    if not count:
        session.add_all(Property(**seed.to_record()) for seed in DEMO_PROPERTIES)
        inserted = len(DEMO_PROPERTIES)
        await session.flush()
    await seed_property_command_center_demo(session)
    await session.commit()
    return inserted


async def seed_property_command_center_demo(session: AsyncSession) -> None:
    """Seed an explicit, deterministic Command Center fixture without external credentials."""
    if await session.get(Campaign, DEMO_CAMPAIGN_ID):
        return

    property_id = DEMO_PROPERTIES[0].id
    prop = await session.get(Property, property_id)
    if not prop:
        return
    base_time = datetime(2026, 9, 18, 12, tzinfo=UTC)

    page_account = ChannelAccount(
        id=DEMO_PAGE_ACCOUNT_ID,
        provider="meta",
        account_type="facebook_page",
        external_account_id="fixture-page-castro",
        display_name="Arriendate Demo · Facebook Page",
        connection_status="fixture",
        capabilities=_capability_map(AccountType.FACEBOOK_PAGE),
        is_demo=True,
        connected_at=base_time - timedelta(days=30),
        last_sync_at=base_time,
        created_at=base_time - timedelta(days=30),
        updated_at=base_time,
    )
    instagram_account = ChannelAccount(
        id=DEMO_INSTAGRAM_ACCOUNT_ID,
        provider="meta",
        account_type="instagram_professional",
        external_account_id="fixture-instagram-castro",
        display_name="Arriendate Demo · Instagram Professional",
        connection_status="fixture",
        capabilities=_capability_map(AccountType.INSTAGRAM_PROFESSIONAL),
        is_demo=True,
        connected_at=base_time - timedelta(days=30),
        last_sync_at=base_time,
        created_at=base_time - timedelta(days=30),
        updated_at=base_time,
    )
    session.add_all([page_account, instagram_account])

    target_specs = (
        (
            UUID("50000000-0000-4000-8000-000000000001"),
            "Facebook Page · Arriendate Demo",
            "facebook_page",
            "api",
            DEMO_PAGE_ACCOUNT_ID,
            "https://example.invalid/facebook/arriendate-demo",
            72,
        ),
        (
            UUID("50000000-0000-4000-8000-000000000002"),
            "Instagram · Arriendate Demo",
            "instagram_professional",
            "api",
            DEMO_INSTAGRAM_ACCOUNT_ID,
            "https://example.invalid/instagram/arriendate-demo",
            72,
        ),
        (
            UUID("50000000-0000-4000-8000-000000000003"),
            "Propiedades Región de Los Lagos",
            "facebook_group",
            "assisted",
            None,
            "https://example.invalid/facebook/groups/propiedades-los-lagos",
            120,
        ),
        (
            UUID("50000000-0000-4000-8000-000000000004"),
            "Compra y Venta Inmobiliaria Sur",
            "facebook_group",
            "assisted",
            None,
            "https://example.invalid/facebook/groups/inmobiliaria-sur",
            72,
        ),
        (
            UUID("50000000-0000-4000-8000-000000000005"),
            "Facebook Marketplace",
            "facebook_marketplace",
            "assisted",
            None,
            "https://example.invalid/facebook/marketplace/create/property",
            168,
        ),
    )
    targets = [
        PublicationTarget(
            id=target_id,
            name=name,
            channel_type=channel_type,
            execution_mode=execution_mode,
            channel_account_id=account_id,
            destination_url=url,
            geographic_relevance="Chile · Demo",
            property_tags=["residencial"],
            active=True,
            minimum_repost_interval_hours=cooldown,
            notes="Registro fixture: no representa una conexión o destino real.",
            is_demo=True,
            created_at=base_time - timedelta(days=20),
            updated_at=base_time,
        )
        for target_id, name, channel_type, execution_mode, account_id, url, cooldown in target_specs
    ]
    session.add_all(targets)

    package = PublicationPackage(
        id=DEMO_PACKAGE_ID,
        property_id=property_id,
        property_fingerprint=compute_property_fingerprint(prop, []),
        status="approved",
        created_at=base_time - timedelta(days=10),
        updated_at=base_time - timedelta(days=9),
    )
    session.add(package)
    variant_content = {
        "facebook_page": (
            "Departamento disponible en Viña del Mar",
            "Conoce esta propiedad luminosa de 2 dormitorios. Escríbenos para coordinar visita.",
        ),
        "instagram_professional": (
            "Nuevo hogar en Viña del Mar",
            "2 dormitorios · 2 baños · balcón. Consulta disponibilidad por DM.",
        ),
        "facebook_group": (
            "[Arriendo] Departamento en Viña del Mar",
            "Hola comunidad. Compartimos propiedad disponible con 2 dormitorios y 2 baños.",
        ),
        "facebook_marketplace": (
            "Departamento 2D/2B en Viña del Mar",
            "Departamento luminoso en sector residencial. Valor y hechos verificados en la ficha.",
        ),
    }
    variants = []
    for index, (channel_type, (headline, body)) in enumerate(variant_content.items(), start=1):
        variants.append(
            PublicationPackageVariant(
                id=UUID(f"31000000-0000-4000-8000-{index:012d}"),
                package_id=DEMO_PACKAGE_ID,
                channel_type=channel_type,
                headline=headline,
                body=body,
                short_body=body,
                highlights=["Precio verificado", "2 dormitorios", "2 baños"],
                cta="Solicitar información y coordinar visita.",
                suggested_media_ids=[],
                warnings=["Datos fixture; no publicar como oferta real."],
                created_at=base_time - timedelta(days=10),
            )
        )
    session.add_all(variants)

    campaign = Campaign(
        id=DEMO_CAMPAIGN_ID,
        property_id=property_id,
        package_id=DEMO_PACKAGE_ID,
        status="active",
        created_at=base_time - timedelta(days=8),
        updated_at=base_time,
    )
    session.add(campaign)
    await session.flush()

    jobs: list[PublicationJob] = []
    campaign_targets: list[CampaignTarget] = []
    for index, target in enumerate(targets, start=1):
        campaign_target = CampaignTarget(
            id=UUID(f"41000000-0000-4000-8000-{index:012d}"),
            campaign_id=DEMO_CAMPAIGN_ID,
            target_id=target.id,
            created_at=base_time - timedelta(days=8),
        )
        campaign_targets.append(campaign_target)
        has_history = index <= 4
        ready_repost = index == 4
        job = PublicationJob(
            id=UUID(f"42000000-0000-4000-8000-{index:012d}"),
            campaign_id=DEMO_CAMPAIGN_ID,
            campaign_target_id=campaign_target.id,
            property_id=property_id,
            target_id=target.id,
            package_id=DEMO_PACKAGE_ID,
            variant_type=target.channel_type,
            execution_mode=target.execution_mode,
            status="ready" if ready_repost or not has_history else "cooldown",
            scheduled_at=base_time,
            next_eligible_at=(
                None
                if ready_repost or not has_history
                else base_time + timedelta(hours=target.minimum_repost_interval_hours)
            ),
            attempt_count=1 if has_history else 0,
            action_required=False,
            created_at=base_time - timedelta(days=8),
            updated_at=base_time,
        )
        jobs.append(job)
    session.add_all(campaign_targets)
    session.add_all(jobs)
    await session.flush()

    publications: list[Publication] = []
    for index, (target, job) in enumerate(zip(targets[:4], jobs[:4], strict=True), start=1):
        publications.append(
            Publication(
                id=UUID(f"60000000-0000-4000-8000-{index:012d}"),
                job_id=job.id,
                property_id=property_id,
                campaign_id=DEMO_CAMPAIGN_ID,
                target_id=target.id,
                package_id=DEMO_PACKAGE_ID,
                channel_account_id=target.channel_account_id,
                variant_type=target.channel_type,
                external_publication_id=f"fixture-publication-{index}",
                published_at=base_time - timedelta(days=index),
                publication_url=f"https://example.invalid/publications/{index}",
                execution_mode=target.execution_mode,
                created_at=base_time - timedelta(days=index),
            )
        )
    session.add_all(publications)
    await session.flush()

    session.add_all(
        [
            EngagementSnapshot(
                id=UUID("70000000-0000-4000-8000-000000000001"),
                publication_id=publications[0].id,
                captured_at=base_time,
                comments_count=2,
                reactions_count=11,
                views_count=None,
                impressions_count=840,
                messages_count=2,
                source="meta_fixture",
                is_demo=True,
                created_at=base_time,
            ),
            EngagementSnapshot(
                id=UUID("70000000-0000-4000-8000-000000000002"),
                publication_id=publications[1].id,
                captured_at=base_time,
                comments_count=1,
                reactions_count=None,
                views_count=None,
                impressions_count=None,
                messages_count=1,
                source="meta_fixture",
                is_demo=True,
                created_at=base_time,
            ),
            EngagementSnapshot(
                id=UUID("70000000-0000-4000-8000-000000000003"),
                publication_id=publications[2].id,
                captured_at=base_time,
                comments_count=None,
                reactions_count=None,
                views_count=None,
                impressions_count=None,
                messages_count=None,
                source="assisted_fixture",
                is_demo=True,
                created_at=base_time,
            ),
        ]
    )
    session.add_all(
        [
            PublicationComment(
                id=UUID("71000000-0000-4000-8000-000000000001"),
                publication_id=publications[0].id,
                external_comment_id="fixture-comment-page-1",
                author_display_name="Persona demo",
                body="¿Sigue disponible para visitar esta semana?",
                created_external_at=base_time - timedelta(hours=3),
                reply_status="needs_reply",
                is_demo=True,
                created_at=base_time - timedelta(hours=3),
            ),
            PublicationComment(
                id=UUID("71000000-0000-4000-8000-000000000002"),
                publication_id=publications[1].id,
                external_comment_id="fixture-comment-instagram-1",
                author_display_name="Cuenta demo",
                body="Me interesa conocer los requisitos.",
                created_external_at=base_time - timedelta(hours=5),
                reply_status="replied",
                is_demo=True,
                created_at=base_time - timedelta(hours=5),
            ),
        ]
    )

    conversation = Conversation(
        id=UUID("80000000-0000-4000-8000-000000000001"),
        channel_account_id=DEMO_PAGE_ACCOUNT_ID,
        external_conversation_id="fixture-messenger-thread-1",
        channel_type="messenger",
        property_id=property_id,
        publication_id=publications[0].id,
        lead_id=None,
        status="needs_reply",
        last_message_at=base_time - timedelta(hours=1),
        is_demo=True,
        created_at=base_time - timedelta(hours=2),
        updated_at=base_time - timedelta(hours=1),
    )
    session.add(conversation)
    await session.flush()
    session.add_all(
        [
            Message(
                id=UUID("81000000-0000-4000-8000-000000000001"),
                conversation_id=conversation.id,
                external_message_id="fixture-message-1",
                direction="inbound",
                sender_display_name="Persona demo",
                message_type="text",
                body="Hola, vi la publicación y quisiera coordinar una visita.",
                sent_at=base_time - timedelta(hours=2),
                is_demo=True,
                created_at=base_time - timedelta(hours=2),
            ),
            Message(
                id=UUID("81000000-0000-4000-8000-000000000002"),
                conversation_id=conversation.id,
                external_message_id="fixture-message-2",
                direction="inbound",
                sender_display_name="Persona demo",
                message_type="text",
                body="¿Tienen disponibilidad el sábado?",
                sent_at=base_time - timedelta(hours=1),
                is_demo=True,
                created_at=base_time - timedelta(hours=1),
            ),
        ]
    )
