from app.core.settings import REPOSITORY_ROOT
from app.evaluation.matching import evaluate_property_matching, evaluation_passed


async def test_versioned_property_matching_dataset_passes() -> None:
    report = await evaluate_property_matching(
        REPOSITORY_ROOT / "evals" / "datasets" / "property_matching.v0.1.json"
    )

    assert evaluation_passed(report)
    assert report["metrics"] == {
        "case_count": 7,
        "schema_validity_rate": 1.0,
        "candidate_set_exact_count": 7,
        "candidate_eligibility_accuracy": 1.0,
        "reviewed_top_k_cases": 7,
        "top_k_exact_count": 7,
        "top_k_accuracy": 1.0,
        "hard_constraint_precision": 1.0,
        "excluded_property_leakage": 0,
        "score_range_validity": 1.0,
        "grounded_reason_validity": 1.0,
        "grounded_reason_count": report["metrics"]["grounded_reason_count"],
    }
    assert report["failures"] == []
