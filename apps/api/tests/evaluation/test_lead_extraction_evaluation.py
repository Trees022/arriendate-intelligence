from decimal import Decimal

from app.core.settings import REPOSITORY_ROOT, Settings
from app.evaluation.lead_extraction import evaluate_lead_extraction, evaluation_passed


async def test_versioned_fixture_dataset_and_invalid_outputs_pass() -> None:
    report = await evaluate_lead_extraction(
        dataset_path=REPOSITORY_ROOT
        / "evals"
        / "datasets"
        / "lead_extraction.v0.1.json",
        invalid_dataset_path=REPOSITORY_ROOT
        / "evals"
        / "datasets"
        / "lead_extraction_invalid.v0.1.json",
        settings=Settings(
            ai_input_cost_per_million=Decimal("1.00"),
            ai_output_cost_per_million=Decimal("6.00"),
        ),
    )

    assert evaluation_passed(report)
    assert report["prompt_version"] == "lead-extraction-v1.0.0"
    assert report["metrics"] == {
        "case_count": 15,
        "schema_valid_count": 15,
        "schema_validity_rate": 1.0,
        "field_matches": 69,
        "field_expectations": 69,
        "field_accuracy": 1.0,
        "invalid_case_count": 7,
        "invalid_rejected_count": 7,
        "invalid_rejection_rate": 1.0,
        "average_latency_ms": report["metrics"]["average_latency_ms"],
        "input_tokens": 1_800,
        "output_tokens": 1_200,
        "estimated_cost_usd": 0.009,
    }
    assert report["failures"] == []
