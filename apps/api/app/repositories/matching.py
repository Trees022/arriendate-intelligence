import math
from collections.abc import Sequence
from datetime import UTC, datetime
from time import perf_counter
from typing import cast
from uuid import UUID

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Lead, LeadRequirement, MatchingRun, Property, PropertyMatch
from app.embeddings.contracts import EmbeddingProvider
from app.embeddings.validation import validate_embeddings
from app.matching.requirements import requirements_fingerprint
from app.matching.text import build_property_embedding_text


def vector_literal(vector: Sequence[float]) -> str:
    return "[" + ",".join(format(float(value), ".12g") for value in vector) + "]"


class MatchingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_properties(self) -> list[Property]:
        rows = await self.session.scalars(select(Property).order_by(Property.id))
        return list(rows)

    async def create_run(
        self,
        *,
        lead_id: UUID,
        provider: str,
        model: str,
        embedding_space_id: str,
        requirements_fingerprint: str,
        algorithm_version: str,
        top_k: int,
    ) -> MatchingRun:
        run = MatchingRun(
            lead_id=lead_id,
            provider=provider,
            model=model,
            embedding_space_id=embedding_space_id,
            requirements_fingerprint=requirements_fingerprint,
            algorithm_version=algorithm_version,
            requested_top_k=top_k,
            status="running",
        )
        self.session.add(run)
        await self.session.commit()
        await self.session.refresh(run)
        return run

    async def ensure_property_embeddings(
        self,
        properties: Sequence[Property],
        provider: EmbeddingProvider,
    ) -> tuple[dict[UUID, list[float]], int]:
        started = perf_counter()
        dialect = self.session.get_bind().dialect.name
        missing_ids: set[UUID] = set()
        if dialect == "postgresql" and properties:
            rows = await self.session.execute(
                text(
                    "select id, embedding is null as missing from public.properties "
                    "where id = any(cast(:ids as uuid[]))"
                ),
                {"ids": [property_record.id for property_record in properties]},
            )
            missing_ids = {row.id for row in rows if row.missing}
        elif dialect != "postgresql":
            missing_ids = {property_record.id for property_record in properties}

        canonical = {
            property_record.id: build_property_embedding_text(property_record)
            for property_record in properties
        }
        stale = [
            property_record
            for property_record in properties
            if property_record.id in missing_ids
            or property_record.embedding_text != canonical[property_record.id]
            or property_record.embedding_provider != provider.provider_name
            or property_record.embedding_model != provider.model
            or property_record.embedding_space_id != provider.space_id
            or property_record.embedding_updated_at is None
        ]
        vectors_by_id: dict[UUID, list[float]] = {}
        if stale:
            vectors = await provider.embed([canonical[item.id] for item in stale])
            validate_embeddings(vectors, expected_count=len(stale), dimension=provider.dimension)
            now = datetime.now(UTC)
            for property_record, vector in zip(stale, vectors, strict=True):
                vectors_by_id[property_record.id] = vector
                property_record.embedding_text = canonical[property_record.id]
                property_record.embedding_provider = provider.provider_name
                property_record.embedding_model = provider.model
                property_record.embedding_space_id = provider.space_id
                property_record.embedding_updated_at = now
                if dialect == "postgresql":
                    await self.session.execute(
                        text(
                            "update public.properties set embedding = cast(:embedding as vector), "
                            "embedding_text = :embedding_text, embedding_provider = :provider, "
                            "embedding_model = :model, embedding_space_id = :space_id, "
                            "embedding_updated_at = :updated_at where id = :property_id"
                        ),
                        {
                            "embedding": vector_literal(vector),
                            "embedding_text": property_record.embedding_text,
                            "provider": provider.provider_name,
                            "model": provider.model,
                            "space_id": provider.space_id,
                            "updated_at": now,
                            "property_id": property_record.id,
                        },
                    )
            await self.session.commit()
        return vectors_by_id, round((perf_counter() - started) * 1000)

    async def rank_candidates(
        self,
        *,
        candidate_ids: Sequence[UUID],
        query_vector: Sequence[float],
        top_k: int,
        in_memory_vectors: dict[UUID, list[float]],
    ) -> list[tuple[UUID, float]]:
        if self.session.get_bind().dialect.name == "postgresql":
            result = await self.session.execute(
                text(
                    "select id, greatest(0.0, least(1.0, "
                    "((1.0 - (embedding <=> cast(:query_embedding as vector))) + 1.0) / 2.0)) "
                    "as score from public.properties "
                    "where id = any(cast(:candidate_ids as uuid[])) and embedding is not null "
                    "order by embedding <=> cast(:query_embedding as vector), id limit :top_k"
                ),
                {
                    "query_embedding": vector_literal(query_vector),
                    "candidate_ids": list(candidate_ids),
                    "top_k": top_k,
                },
            )
            return [(row.id, float(row.score)) for row in result]

        scored = [
            (property_id, self._cosine_score(query_vector, in_memory_vectors[property_id]))
            for property_id in candidate_ids
        ]
        return sorted(scored, key=lambda item: (-item[1], str(item[0])))[:top_k]

    async def complete_run(
        self,
        *,
        run: MatchingRun,
        total_properties: int,
        candidate_count: int,
        latency_ms: int,
        embedding_latency_ms: int,
        exclusion_summary: list[dict[str, object]],
        matches: Sequence[dict[str, object]],
    ) -> bool:
        current_requirements = await self.session.scalar(
            select(LeadRequirement)
            .where(LeadRequirement.lead_id == run.lead_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        locked_run = await self.session.scalar(
            select(MatchingRun)
            .where(MatchingRun.id == run.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if current_requirements is None or locked_run is None:
            raise RuntimeError("Matching state disappeared during completion")
        is_current = (
            locked_run.invalidated_at is None
            and requirements_fingerprint(current_requirements)
            == locked_run.requirements_fingerprint
        )
        if not is_current and locked_run.invalidated_at is None:
            locked_run.invalidated_at = datetime.now(UTC)
        locked_run.total_properties = total_properties
        locked_run.candidate_count = candidate_count
        locked_run.result_count = len(matches)
        locked_run.latency_ms = latency_ms
        locked_run.embedding_latency_ms = embedding_latency_ms
        locked_run.exclusion_summary = exclusion_summary
        locked_run.status = "succeeded"
        locked_run.error_code = None
        locked_run.error_message = None
        for values in matches:
            self.session.add(
                PropertyMatch(run_id=locked_run.id, lead_id=locked_run.lead_id, **values)
            )
        if is_current and matches:
            lead = await self.session.get(Lead, locked_run.lead_id)
            if lead is None:
                raise RuntimeError("Lead disappeared during matching completion")
            lead.status = "matched"
        await self.session.commit()
        await self.session.refresh(locked_run)
        return is_current

    async def fail_run(
        self,
        run_id: UUID,
        *,
        total_properties: int,
        candidate_count: int,
        latency_ms: int,
        embedding_latency_ms: int,
        exclusion_summary: list[dict[str, object]],
        error_code: str,
        error_message: str,
    ) -> None:
        run = await self.session.get(MatchingRun, run_id)
        if run is None:
            raise RuntimeError("Matching run disappeared during failure persistence")
        await self.session.execute(delete(PropertyMatch).where(PropertyMatch.run_id == run.id))
        run.total_properties = total_properties
        run.candidate_count = candidate_count
        run.result_count = 0
        run.status = "failed"
        run.latency_ms = latency_ms
        run.embedding_latency_ms = embedding_latency_ms
        run.exclusion_summary = exclusion_summary
        run.error_code = error_code[:80]
        run.error_message = error_message[:300]
        await self.session.commit()

    async def latest_successful_run(
        self, lead_id: UUID, *, requirements_fingerprint: str
    ) -> MatchingRun | None:
        return cast(
            MatchingRun | None,
            await self.session.scalar(
                select(MatchingRun)
                .where(
                    MatchingRun.lead_id == lead_id,
                    MatchingRun.status == "succeeded",
                    MatchingRun.invalidated_at.is_(None),
                    MatchingRun.requirements_fingerprint == requirements_fingerprint,
                )
                .order_by(MatchingRun.created_at.desc(), MatchingRun.id.desc())
                .limit(1)
            ),
        )

    async def matches_for_run(self, run_id: UUID) -> list[tuple[PropertyMatch, Property]]:
        rows = await self.session.execute(
            select(PropertyMatch, Property)
            .join(Property, Property.id == PropertyMatch.property_id)
            .where(PropertyMatch.run_id == run_id)
            .order_by(PropertyMatch.rank)
        )
        return list(rows.tuples())

    @staticmethod
    def _cosine_score(left: Sequence[float], right: Sequence[float]) -> float:
        dot = sum(a * b for a, b in zip(left, right, strict=True))
        left_norm = math.sqrt(sum(value * value for value in left))
        right_norm = math.sqrt(sum(value * value for value in right))
        similarity = dot / (left_norm * right_norm) if left_norm and right_norm else 0.0
        return max(0.0, min(1.0, (similarity + 1.0) / 2.0))
