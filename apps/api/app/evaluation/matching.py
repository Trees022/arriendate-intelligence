import argparse
import asyncio
import json
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from anyio import Path as AsyncPath
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.ai.schemas import LeadRequirements
from app.core.settings import REPOSITORY_ROOT
from app.data.properties import DEMO_PROPERTIES
from app.db.models import LeadRequirement, Property
from app.embeddings.providers.deterministic import DeterministicEmbeddingProvider
from app.matching.constraints import ConstraintEvaluator
from app.matching.text import build_lead_semantic_text, build_property_embedding_text
from app.services.matching import ALGORITHM_VERSION, PropertyMatchingService


class MatchingEvaluationCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    scenario: str = Field(min_length=1)
    original_request: str = Field(min_length=10)
    requirements: LeadRequirements
    top_k: int = Field(ge=1, le=10)
    expected_candidate_ids: list[UUID]
    expected_top_ids: list[UUID] | None


class MatchingEvaluationDataset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str = Field(min_length=1)
    cases: list[MatchingEvaluationCase] = Field(min_length=1)

    @model_validator(mode="after")
    def reject_duplicate_ids(self) -> "MatchingEvaluationDataset":
        ids = [case.id for case in self.cases]
        if len(ids) != len(set(ids)):
            raise ValueError("evaluation case IDs must be unique")
        return self


def _database_requirements(requirements: LeadRequirements) -> LeadRequirement:
    return LeadRequirement(
        lead_id=UUID(int=0),
        operation_type=requirements.operation_type.value,
        property_types=[value.value for value in requirements.property_types],
        locations=requirements.locations,
        max_budget=requirements.max_budget,
        currency=requirements.currency.value if requirements.currency else None,
        min_bedrooms=requirements.min_bedrooms,
        min_bathrooms=requirements.min_bathrooms,
        parking_required=requirements.parking_required,
        pets_required=requirements.pets_required,
        furnished_preference=requirements.furnished_preference,
        soft_preferences=requirements.soft_preferences,
        missing_information=[value.value for value in requirements.missing_information],
        extraction_confidence=requirements.confidence,
        extraction_model="evaluation-fixture",
        prompt_version="evaluation-fixture-v1",
    )


def _cosine_score(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    similarity = dot / (left_norm * right_norm) if left_norm and right_norm else 0.0
    return max(0.0, min(1.0, (similarity + 1.0) / 2.0))


def _reason_is_grounded(
    reason: dict[str, str], property_record: Property, requirements: LeadRequirement
) -> bool:
    permitted_preferences = set(requirements.soft_preferences)
    if requirements.furnished_preference is not None:
        permitted_preferences.add(
            "amoblado" if requirements.furnished_preference else "sin amoblar"
        )
    permitted_facts = {property_record.description}
    if property_record.sector:
        permitted_facts.add(f"Sector: {property_record.sector}")
    permitted_facts.update(f"Comodidad: {value}" for value in property_record.amenities)
    if property_record.furnished is not None:
        permitted_facts.add(
            "La propiedad está amoblada"
            if property_record.furnished
            else "La propiedad no está amoblada"
        )
    return (
        reason.get("preference") in permitted_preferences
        and reason.get("property_fact") in permitted_facts
    )


async def evaluate_property_matching(dataset_path: Path) -> dict[str, Any]:
    dataset_text = await AsyncPath(dataset_path).read_text(encoding="utf-8")
    dataset = MatchingEvaluationDataset.model_validate_json(
        dataset_text
    )
    properties = [Property(**seed.to_record()) for seed in DEMO_PROPERTIES]
    property_by_id = {item.id: item for item in properties}
    evaluator = ConstraintEvaluator()
    provider = DeterministicEmbeddingProvider()

    candidate_exact = 0
    top_k_exact = 0
    reviewed_top_k_cases = 0
    ranked_count = 0
    eligible_ranked_count = 0
    leakage_count = 0
    scored_count = 0
    valid_score_count = 0
    reason_count = 0
    grounded_reason_count = 0
    failures: list[dict[str, str]] = []
    observed_rankings: dict[str, list[str]] = {}

    for case in dataset.cases:
        requirements = _database_requirements(case.requirements)
        evaluations = {
            item.id: evaluator.evaluate(item, requirements) for item in properties
        }
        candidates = [item for item in properties if evaluations[item.id].eligible]
        candidate_ids = [item.id for item in candidates]
        if set(candidate_ids) == set(case.expected_candidate_ids):
            candidate_exact += 1
        else:
            failures.append({"case_id": case.id, "reason": "candidate_set_mismatch"})

        semantic_text = build_lead_semantic_text(requirements)
        ranked: list[tuple[UUID, float | None]]
        if semantic_text and candidates:
            property_vectors = await provider.embed(
                [build_property_embedding_text(item) for item in candidates]
            )
            query_vector = (await provider.embed([semantic_text]))[0]
            scored = [
                (item.id, _cosine_score(query_vector, vector))
                for item, vector in zip(candidates, property_vectors, strict=True)
            ]
            ranked = [
                (property_id, score)
                for property_id, score in sorted(
                    scored, key=lambda item: (-item[1], str(item[0]))
                )[: case.top_k]
            ]
        else:
            ranked = [(item.id, None) for item in candidates[: case.top_k]]

        ranked_ids = [item[0] for item in ranked]
        observed_rankings[case.id] = [str(value) for value in ranked_ids]
        if case.expected_top_ids is not None:
            reviewed_top_k_cases += 1
            if ranked_ids == case.expected_top_ids:
                top_k_exact += 1
            else:
                failures.append({"case_id": case.id, "reason": "top_k_mismatch"})

        for property_id, score in ranked:
            ranked_count += 1
            if evaluations[property_id].eligible:
                eligible_ranked_count += 1
            else:
                leakage_count += 1
            if score is not None:
                scored_count += 1
                if 0 <= score <= 1:
                    valid_score_count += 1
            property_record = property_by_id[property_id]
            reasons = PropertyMatchingService._soft_reasons(property_record, requirements)
            for reason in reasons:
                reason_count += 1
                if _reason_is_grounded(reason, property_record, requirements):
                    grounded_reason_count += 1
                else:
                    failures.append({"case_id": case.id, "reason": "ungrounded_reason"})

    case_count = len(dataset.cases)
    return {
        "evaluation": "property_matching",
        "dataset_version": dataset.version,
        "algorithm_version": ALGORITHM_VERSION,
        "provider": provider.provider_name,
        "model": provider.model,
        "generated_at": datetime.now(UTC).isoformat(),
        "metrics": {
            "case_count": case_count,
            "schema_validity_rate": 1.0,
            "candidate_set_exact_count": candidate_exact,
            "candidate_eligibility_accuracy": candidate_exact / case_count,
            "reviewed_top_k_cases": reviewed_top_k_cases,
            "top_k_exact_count": top_k_exact,
            "top_k_accuracy": (
                top_k_exact / reviewed_top_k_cases if reviewed_top_k_cases else 1.0
            ),
            "hard_constraint_precision": (
                eligible_ranked_count / ranked_count if ranked_count else 1.0
            ),
            "excluded_property_leakage": leakage_count,
            "score_range_validity": valid_score_count / scored_count if scored_count else 1.0,
            "grounded_reason_validity": (
                grounded_reason_count / reason_count if reason_count else 1.0
            ),
            "grounded_reason_count": reason_count,
        },
        "observed_rankings": observed_rankings,
        "failures": failures,
    }


def evaluation_passed(report: dict[str, Any]) -> bool:
    metrics = report["metrics"]
    return bool(
        metrics["schema_validity_rate"] == 1
        and metrics["candidate_eligibility_accuracy"] == 1
        and metrics["top_k_accuracy"] == 1
        and metrics["hard_constraint_precision"] == 1
        and metrics["excluded_property_leakage"] == 0
        and metrics["score_range_validity"] == 1
        and metrics["grounded_reason_validity"] == 1
        and not report["failures"]
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate deterministic property matching")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=REPOSITORY_ROOT / "evals" / "datasets" / "property_matching.v0.1.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPOSITORY_ROOT / "evals" / "results" / "property_matching.latest.json",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        report = asyncio.run(evaluate_property_matching(args.dataset))
    except (OSError, ValueError) as error:
        print(f"Evaluation could not run: {error}")
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if evaluation_passed(report) else 1
