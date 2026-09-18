from collections.abc import Iterable
from uuid import UUID

from app.api.schemas import PropertyActionResponse
from app.db.models import (
    Campaign,
    Conversation,
    Property,
    Publication,
    PublicationComment,
    PublicationJob,
    PublicationTarget,
)
from app.domain.enums import CampaignStatus, ConversationStatus, JobStatus, ReplyStatus

_PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def compute_property_actions(
    *,
    prop: Property,
    targets: Iterable[PublicationTarget],
    jobs: Iterable[PublicationJob],
    publications: Iterable[Publication],
    conversations: Iterable[Conversation],
    comments: Iterable[PublicationComment],
    campaigns: Iterable[Campaign],
    package_is_stale: bool,
    media_count: int,
) -> list[PropertyActionResponse]:
    actions: list[PropertyActionResponse] = []
    jobs_by_target: dict[UUID, PublicationJob] = {}
    for existing_job in jobs:
        jobs_by_target.setdefault(existing_job.target_id, existing_job)
    published_targets = {publication.target_id for publication in publications}

    if package_is_stale:
        actions.append(
            PropertyActionResponse(
                type="stale_package",
                priority="high",
                title="Actualizar paquete de publicación",
                description="Los datos o fotos cambiaron desde la última versión aprobada.",
                related_entity_type="property",
                related_entity_id=prop.id,
            )
        )

    if media_count == 0:
        actions.append(
            PropertyActionResponse(
                type="missing_marketing_data",
                priority="high",
                title="Agregar fotos de la propiedad",
                description="El paquete puede prepararse, pero aún no tiene material visual.",
                related_entity_type="property",
                related_entity_id=prop.id,
            )
        )

    for target in targets:
        job = jobs_by_target.get(target.id)
        if job is None:
            actions.append(
                PropertyActionResponse(
                    type="initial_publication",
                    priority="medium",
                    title=f"Preparar publicación en {target.name}",
                    description="Este destino activo aún no forma parte de una campaña.",
                    related_entity_type="publication_target",
                    related_entity_id=target.id,
                )
            )
            continue
        if job.status == JobStatus.FAILED.value:
            actions.append(
                PropertyActionResponse(
                    type="failed_job",
                    priority="high",
                    title=f"Resolver error en {target.name}",
                    description=job.error_message or "La publicación no pudo completarse.",
                    related_entity_type="publication_job",
                    related_entity_id=job.id,
                )
            )
        elif job.action_required:
            actions.append(
                PropertyActionResponse(
                    type="job_requires_action",
                    priority="high",
                    title=f"Revisar {target.name}",
                    description=job.action_note or "El trabajo requiere intervención del operador.",
                    related_entity_type="publication_job",
                    related_entity_id=job.id,
                )
            )
        elif job.status == JobStatus.READY.value:
            is_repost = target.id in published_targets
            actions.append(
                PropertyActionResponse(
                    type="ready_to_repost" if is_repost else "initial_publication",
                    priority="medium",
                    title=(
                        f"Republicar en {target.name}"
                        if is_repost
                        else f"Publicar en {target.name}"
                    ),
                    description=(
                        "El cooldown terminó y el destino vuelve a estar disponible."
                        if is_repost
                        else "El contenido está preparado para este destino."
                    ),
                    related_entity_type="publication_job",
                    related_entity_id=job.id,
                )
            )

    needs_reply = [
        conversation
        for conversation in conversations
        if conversation.status == ConversationStatus.NEEDS_REPLY.value
    ]
    if needs_reply:
        actions.append(
            PropertyActionResponse(
                type="conversation_needs_reply",
                priority="high",
                title="Responder conversación nueva",
                description=(
                    f"Hay {len(needs_reply)} conversación(es) vinculada(s) "
                    "esperando respuesta."
                ),
                related_entity_type="conversation",
                related_entity_id=needs_reply[0].id,
            )
        )

    comments_to_reply = [
        comment
        for comment in comments
        if comment.reply_status in {ReplyStatus.NEW.value, ReplyStatus.NEEDS_REPLY.value}
    ]
    if comments_to_reply:
        actions.append(
            PropertyActionResponse(
                type="comment_needs_reply",
                priority="medium",
                title="Revisar comentarios recientes",
                description=f"Hay {len(comments_to_reply)} comentario(s) pendiente(s).",
                related_entity_type="publication_comment",
                related_entity_id=comments_to_reply[0].id,
            )
        )

    paused = [
        campaign
        for campaign in campaigns
        if campaign.status == CampaignStatus.PAUSED.value
    ]
    if paused:
        actions.append(
            PropertyActionResponse(
                type="campaign_paused",
                priority="low",
                title="Revisar campaña pausada",
                description="Los trabajos no avanzarán hasta reanudar o cerrar la campaña.",
                related_entity_type="campaign",
                related_entity_id=paused[0].id,
            )
        )

    return sorted(actions, key=lambda item: (_PRIORITY_ORDER[item.priority], item.title))
