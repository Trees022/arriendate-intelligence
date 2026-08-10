import argparse
import asyncio
import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from time import perf_counter
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from app.ai.contracts import StructuredGenerationResult, StructuredGenerator
from app.ai.costs import estimate_token_cost
from app.ai.factory import build_structured_generator
from app.ai.prompts import PROMPT_VERSION, build_lead_extraction_request
from app.ai.providers.fixture import StaticStructuredGenerator
from app.ai.schemas import LeadRequirements
from app.core.settings import REPOSITORY_ROOT, Settings


class EvaluationCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    scenario: str = Field(min_length=1)
    original_request: str = Field(min_length=10)
    expected: dict[str, Any]
    fixture_output: dict[str, Any]


class EvaluationDataset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str
    cases: list[EvaluationCase] = Field(min_length=1)

    @model_validator(mode="after")
    def reject_duplicate_ids(self) -> "EvaluationDataset":
        ids = [case.id for case in self.cases]
        if len(ids) != len(set(ids)):
            raise ValueError("evaluation case IDs must be unique")
        return self


class InvalidEvaluationCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    scenario: str = Field(min_length=1)
    fixture_output: str | dict[str, Any]


class InvalidEvaluationDataset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str
    cases: list[InvalidEvaluationCase] = Field(min_length=1)


def _read_dataset(path: Path, model: type[BaseModel]) -> BaseModel:
    return model.model_validate_json(path.read_text(encoding="utf-8"))


def _as_json_text(value: str | dict[str, Any]) -> str:
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)


async def _generate_case(
    case: EvaluationCase,
    *,
    mode: Literal["fixture", "live"],
    live_generator: StructuredGenerator | None,
) -> tuple[StructuredGenerationResult, float]:
    generator: StructuredGenerator
    if mode == "fixture":
        generator = StaticStructuredGenerator(_as_json_text(case.fixture_output))
    elif live_generator is not None:
        generator = live_generator
    else:  # pragma: no cover - guarded by the CLI and public evaluator
        raise RuntimeError("live generator is required in live mode")

    started = perf_counter()
    result = await generator.generate_structured(
        build_lead_extraction_request(case.original_request)
    )
    return result, (perf_counter() - started) * 1000


async def evaluate_lead_extraction(
    *,
    dataset_path: Path,
    invalid_dataset_path: Path,
    mode: Literal["fixture", "live"] = "fixture",
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Evaluate schema validity and labeled extraction fields without persisting raw output."""
    resolved_settings = settings or Settings()
    dataset = _read_dataset(dataset_path, EvaluationDataset)
    invalid_dataset = _read_dataset(invalid_dataset_path, InvalidEvaluationDataset)
    assert isinstance(dataset, EvaluationDataset)
    assert isinstance(invalid_dataset, InvalidEvaluationDataset)

    live_generator: StructuredGenerator | None = None
    if mode == "live":
        live_generator = build_structured_generator(resolved_settings)
        if live_generator.provider_name == "disabled":
            raise RuntimeError(
                "Live evaluation requires ARRIENDATE_AI_PROVIDER=openai_compatible "
                "and ARRIENDATE_AI_API_KEY"
            )

    schema_valid = 0
    field_matches = 0
    field_expectations = 0
    total_latency_ms = 0.0
    total_input_tokens = 0
    total_output_tokens = 0
    usage_complete = True
    costs: list[Decimal] = []
    failures: list[dict[str, str]] = []
    observed_provider = "fixture"
    observed_model = "fixture-structured-v1"

    for case in dataset.cases:
        try:
            result, latency_ms = await _generate_case(
                case,
                mode=mode,
                live_generator=live_generator,
            )
            total_latency_ms += latency_ms
            observed_provider = result.provider
            observed_model = result.model
            parsed = LeadRequirements.model_validate_json(result.output_text)
        except Exception as error:
            failures.append(
                {
                    "case_id": case.id,
                    "reason": f"schema_or_provider_error:{type(error).__name__}",
                }
            )
            continue

        schema_valid += 1
        actual = parsed.model_dump(mode="json")
        for field, expected_value in case.expected.items():
            field_expectations += 1
            if actual.get(field) == expected_value:
                field_matches += 1
            else:
                failures.append({"case_id": case.id, "reason": f"field_mismatch:{field}"})

        if result.input_tokens is None or result.output_tokens is None:
            usage_complete = False
        else:
            total_input_tokens += result.input_tokens
            total_output_tokens += result.output_tokens
            estimated = estimate_token_cost(
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                input_cost_per_million=resolved_settings.ai_input_cost_per_million,
                output_cost_per_million=resolved_settings.ai_output_cost_per_million,
            )
            if estimated is not None:
                costs.append(estimated)

    invalid_rejected = 0
    for invalid_case in invalid_dataset.cases:
        try:
            LeadRequirements.model_validate_json(_as_json_text(invalid_case.fixture_output))
        except ValidationError:
            invalid_rejected += 1
        else:
            failures.append(
                {"case_id": invalid_case.id, "reason": "invalid_output_was_accepted"}
            )

    case_count = len(dataset.cases)
    invalid_count = len(invalid_dataset.cases)
    pricing_configured = (
        resolved_settings.ai_input_cost_per_million is not None
        and resolved_settings.ai_output_cost_per_million is not None
    )
    return {
        "evaluation": "lead_extraction",
        "dataset_version": dataset.version,
        "invalid_dataset_version": invalid_dataset.version,
        "prompt_version": PROMPT_VERSION,
        "mode": mode,
        "provider": observed_provider,
        "model": observed_model,
        "generated_at": datetime.now(UTC).isoformat(),
        "metrics": {
            "case_count": case_count,
            "schema_valid_count": schema_valid,
            "schema_validity_rate": schema_valid / case_count,
            "field_matches": field_matches,
            "field_expectations": field_expectations,
            "field_accuracy": field_matches / field_expectations if field_expectations else 0.0,
            "invalid_case_count": invalid_count,
            "invalid_rejected_count": invalid_rejected,
            "invalid_rejection_rate": invalid_rejected / invalid_count,
            "average_latency_ms": round(total_latency_ms / case_count, 3),
            "input_tokens": total_input_tokens if usage_complete else None,
            "output_tokens": total_output_tokens if usage_complete else None,
            "estimated_cost_usd": (
                float(sum(costs, start=Decimal(0)))
                if pricing_configured and len(costs) == schema_valid
                else None
            ),
        },
        "failures": failures,
    }


def evaluation_passed(report: dict[str, Any]) -> bool:
    metrics = report["metrics"]
    return bool(
        metrics["schema_validity_rate"] == 1
        and metrics["field_accuracy"] == 1
        and metrics["invalid_rejection_rate"] == 1
        and not report["failures"]
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate structured lead extraction")
    parser.add_argument("--mode", choices=("fixture", "live"), default="fixture")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=REPOSITORY_ROOT / "evals" / "datasets" / "lead_extraction.v0.1.json",
    )
    parser.add_argument(
        "--invalid-dataset",
        type=Path,
        default=REPOSITORY_ROOT / "evals" / "datasets" / "lead_extraction_invalid.v0.1.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPOSITORY_ROOT / "evals" / "results" / "lead_extraction.latest.json",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        report = asyncio.run(
            evaluate_lead_extraction(
                dataset_path=args.dataset,
                invalid_dataset_path=args.invalid_dataset,
                mode=args.mode,
            )
        )
    except (OSError, ValidationError, RuntimeError) as error:
        print(f"Evaluation could not run: {error}")
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if evaluation_passed(report) else 1


if __name__ == "__main__":
    raise SystemExit(main())
