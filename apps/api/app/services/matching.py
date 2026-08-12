import logging
import re
import unicodedata
from collections import Counter
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from time import perf_counter
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, EmbeddingProviderUnavailableError
from app.db.models import LeadRequirement, MatchingRun, Property, PropertyMatch
from app.embeddings.contracts import EmbeddingProvider
from app.embeddings.errors import EmbeddingError
from app.embeddings.identity import embedding_space_id
from app.embeddings.validation import validate_embeddings
from app.matching.constraints import ConstraintEvaluation, ConstraintEvaluator
from app.matching.requirements import matching_requirements_error, requirements_fingerprint
from app.matching.text import build_lead_semantic_text
from app.repositories.extractions import ExtractionRepository
from app.repositories.matching import MatchingRepository
from app.services.leads import LeadService

LOGGER = logging.getLogger(__name__)
ALGORITHM_VERSION = "hard-semantic-v1"
STOPWORDS = {"para", "como", "algo", "ideal", "sector", "cerca", "desde", "esta", "este"}
TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
NOT_REQUIRED_SPACE_ID = embedding_space_id(
    provider="not_required", model="not_required", dimension=1536
)


@dataclass(frozen=True, slots=True)
class MatchView:
    match: PropertyMatch
    property: Property


@dataclass(frozen=True, slots=True)
class MatchingView:
    run: MatchingRun | None
    items: tuple[MatchView, ...]


class PropertyMatchingService:
    def __init__(self, session: AsyncSession, provider: EmbeddingProvider) -> None:
        self.session = session
        self.provider = provider
        self.repository = MatchingRepository(session)
        self.extractions = ExtractionRepository(session)
        self.leads = LeadService(session)
        self.evaluator = ConstraintEvaluator()

    async def match(self, lead_id: UUID, *, top_k: int) -> MatchingView:
        started = perf_counter()
        await self.leads.get(lead_id)
        requirements = await self.extractions.get_requirements(lead_id)
        if requirements is None:
            raise ConflictError("El lead debe tener requisitos estructurados antes del matching")
        requirement_error = matching_requirements_error(requirements)
        if requirement_error is not None:
            raise ConflictError(requirement_error)
        requirement_fingerprint = requirements_fingerprint(requirements)

        properties = await self.repository.list_properties()
        evaluations = {
            property_record.id: self.evaluator.evaluate(property_record, requirements)
            for property_record in properties
        }
        candidates = [item for item in properties if evaluations[item.id].eligible]
        exclusion_summary = self._exclusion_summary(evaluations.values())
        semantic_text = build_lead_semantic_text(requirements)
        provider_name = (
            self.provider.provider_name if semantic_text and candidates else "not_required"
        )
        model = self.provider.model if semantic_text and candidates else "not_required"
        space_id = self.provider.space_id if semantic_text and candidates else NOT_REQUIRED_SPACE_ID
        run = await self.repository.create_run(
            lead_id=lead_id,
            provider=provider_name,
            model=model,
            embedding_space_id=space_id,
            requirements_fingerprint=requirement_fingerprint,
            algorithm_version=ALGORITHM_VERSION,
            top_k=top_k,
        )

        embedding_latency_ms = 0
        embedding_stage_started: float | None = None
        try:
            if not candidates:
                ranked: list[tuple[UUID, float | None]] = []
            elif semantic_text is None:
                ranked = [(item.id, None) for item in candidates[:top_k]]
            else:
                embedding_stage_started = perf_counter()
                in_memory_vectors, property_latency = (
                    await self.repository.ensure_property_embeddings(candidates, self.provider)
                )
                embedding_started = perf_counter()
                query_vectors = await self.provider.embed([semantic_text])
                validate_embeddings(
                    query_vectors, expected_count=1, dimension=self.provider.dimension
                )
                query_latency = round((perf_counter() - embedding_started) * 1000)
                embedding_latency_ms = property_latency + query_latency
                ranked = [
                    (property_id, score)
                    for property_id, score in await self.repository.rank_candidates(
                        candidate_ids=[item.id for item in candidates],
                        query_vector=query_vectors[0],
                        top_k=top_k,
                        in_memory_vectors=in_memory_vectors,
                    )
                ]

            properties_by_id = {item.id: item for item in candidates}
            match_values: list[dict[str, object]] = []
            for rank, (property_id, score) in enumerate(ranked, start=1):
                property_record = properties_by_id[property_id]
                checks = evaluations[property_id].checks
                match_values.append(
                    {
                        "property_id": property_id,
                        "rank": rank,
                        "semantic_score": score,
                        "hard_constraint_matches": [asdict(check) for check in checks],
                        "soft_match_reasons": self._soft_reasons(property_record, requirements),
                        "algorithm_version": ALGORITHM_VERSION,
                        "embedding_model": self.provider.model if score is not None else None,
                    }
                )

            latency_ms = round((perf_counter() - started) * 1000)
            is_current = await self.repository.complete_run(
                run=run,
                total_properties=len(properties),
                candidate_count=len(candidates),
                latency_ms=latency_ms,
                embedding_latency_ms=embedding_latency_ms,
                exclusion_summary=exclusion_summary,
                matches=match_values,
            )
            LOGGER.info(
                "property_matching_succeeded lead_id=%s run_id=%s total=%s candidates=%s "
                "top_k=%s results=%s latency_ms=%s embedding_latency_ms=%s provider=%s model=%s",
                lead_id,
                run.id,
                len(properties),
                len(candidates),
                top_k,
                len(match_values),
                latency_ms,
                embedding_latency_ms,
                provider_name,
                model,
            )
        except EmbeddingError as error:
            latency_ms = round((perf_counter() - started) * 1000)
            if embedding_stage_started is not None:
                embedding_latency_ms = round(
                    (perf_counter() - embedding_stage_started) * 1000
                )
            await self._best_effort_fail(
                run_id=run.id,
                total_properties=len(properties),
                candidate_count=len(candidates),
                latency_ms=latency_ms,
                embedding_latency_ms=embedding_latency_ms,
                exclusion_summary=exclusion_summary,
                error_code=error.code,
                error_message=error.safe_message,
            )
            LOGGER.warning(
                "property_matching_failed lead_id=%s run_id=%s code=%s latency_ms=%s",
                lead_id,
                run.id,
                error.code,
                latency_ms,
            )
            raise EmbeddingProviderUnavailableError(
                error.safe_message, timeout=error.timeout
            ) from error
        except Exception:
            await self._best_effort_fail(
                run_id=run.id,
                total_properties=len(properties),
                candidate_count=len(candidates),
                latency_ms=round((perf_counter() - started) * 1000),
                embedding_latency_ms=embedding_latency_ms,
                exclusion_summary=exclusion_summary,
                error_code="matching_internal_error",
                error_message="El matching no pudo completarse por un error interno",
            )
            raise

        if not is_current:
            raise ConflictError(
                "Los requisitos cambiaron durante el matching; ejecuta el matching nuevamente"
            )

        return await self.get_latest(lead_id)

    async def get_latest(self, lead_id: UUID) -> MatchingView:
        await self.leads.get(lead_id)
        requirements = await self.extractions.get_requirements(lead_id)
        if requirements is None:
            return MatchingView(run=None, items=())
        run = await self.repository.latest_successful_run(
            lead_id,
            requirements_fingerprint=requirements_fingerprint(requirements),
        )
        if run is None:
            return MatchingView(run=None, items=())
        rows = await self.repository.matches_for_run(run.id)
        return MatchingView(
            run=run,
            items=tuple(
                MatchView(match=match, property=property_record)
                for match, property_record in rows
            ),
        )

    @staticmethod
    def _exclusion_summary(
        evaluations: Iterable[ConstraintEvaluation],
    ) -> list[dict[str, object]]:
        counts: Counter[str] = Counter()
        for evaluation in evaluations:
            for failure in evaluation.failures:
                counts[failure.constraint] += 1
        return [
            {"constraint": constraint, "excluded_count": count}
            for constraint, count in sorted(counts.items())
        ]

    @staticmethod
    def _soft_reasons(
        property_record: Property, requirements: LeadRequirement
    ) -> list[dict[str, str]]:
        facts = [property_record.description]
        if property_record.sector:
            facts.append(f"Sector: {property_record.sector}")
        facts.extend(f"Comodidad: {amenity}" for amenity in property_record.amenities)
        reasons: list[dict[str, str]] = []
        for preference in requirements.soft_preferences:
            tokens = PropertyMatchingService._normalized_tokens(preference)
            fact = next(
                (
                    candidate
                    for candidate in facts
                    if tokens & PropertyMatchingService._normalized_tokens(candidate)
                ),
                None,
            )
            if fact:
                reasons.append({"preference": preference, "property_fact": fact})
        if (
            requirements.furnished_preference is not None
            and property_record.furnished == requirements.furnished_preference
        ):
            reasons.append(
                {
                    "preference": (
                        "amoblado" if requirements.furnished_preference else "sin amoblar"
                    ),
                    "property_fact": (
                        "La propiedad está amoblada"
                        if property_record.furnished
                        else "La propiedad no está amoblada"
                    ),
                }
            )
        return reasons

    async def _best_effort_fail(
        self,
        *,
        run_id: UUID,
        total_properties: int,
        candidate_count: int,
        latency_ms: int,
        embedding_latency_ms: int,
        exclusion_summary: list[dict[str, object]],
        error_code: str,
        error_message: str,
    ) -> None:
        try:
            await self.session.rollback()
            await self.repository.fail_run(
                run_id,
                total_properties=total_properties,
                candidate_count=candidate_count,
                latency_ms=latency_ms,
                embedding_latency_ms=embedding_latency_ms,
                exclusion_summary=exclusion_summary,
                error_code=error_code,
                error_message=error_message,
            )
        except Exception:
            await self.session.rollback()

    @staticmethod
    def _normalized_tokens(text: str) -> set[str]:
        decomposed = unicodedata.normalize("NFKD", text.casefold())
        normalized = "".join(
            character for character in decomposed if not unicodedata.combining(character)
        )
        return {
            token
            for token in TOKEN_PATTERN.findall(normalized)
            if len(token) >= 3 and token not in STOPWORDS
        }
