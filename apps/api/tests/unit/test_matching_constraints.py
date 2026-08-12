from uuid import uuid4

from app.db.models import LeadRequirement, Property
from app.matching.constraints import ConstraintEvaluator
from app.services.matching import PropertyMatchingService


def property_record(**overrides: object) -> Property:
    values: dict[str, object] = {
        "id": uuid4(),
        "title": "Departamento sintético",
        "description": "Departamento luminoso con balcón.",
        "operation_type": "rent",
        "property_type": "apartment",
        "city": "Viña del Mar",
        "sector": "Recreo",
        "monthly_price": 700_000,
        "sale_price": None,
        "currency": "CLP",
        "bedrooms": 2,
        "bathrooms": 2,
        "parking_spaces": 1,
        "pet_policy": "allowed",
        "furnished": False,
        "square_meters": 70,
        "amenities": ["balcón"],
        "availability_status": "available",
        "source_text": "fuente",
        "embedding_text": "texto",
    }
    values.update(overrides)
    return Property(**values)


def requirements(**overrides: object) -> LeadRequirement:
    values: dict[str, object] = {
        "id": uuid4(),
        "lead_id": uuid4(),
        "operation_type": "unknown",
        "property_types": [],
        "locations": [],
        "max_budget": None,
        "currency": None,
        "min_bedrooms": None,
        "min_bathrooms": None,
        "parking_required": None,
        "pets_required": None,
        "furnished_preference": None,
        "soft_preferences": [],
        "missing_information": [],
        "extraction_confidence": 1,
        "extraction_model": "fixture",
        "prompt_version": "fixture",
    }
    values.update(overrides)
    return LeadRequirement(**values)


def failure_names(result) -> list[str]:
    return [failure.constraint for failure in result.failures]


def test_absent_requirements_do_not_filter_available_property() -> None:
    result = ConstraintEvaluator().evaluate(property_record(), requirements())
    assert result.eligible
    assert [check.constraint for check in result.checks] == ["availability"]


def test_budget_passes_at_limit_and_excludes_above_limit() -> None:
    expected = requirements(operation_type="rent", max_budget=700_000, currency="CLP")
    assert ConstraintEvaluator().evaluate(property_record(), expected).eligible
    failure = ConstraintEvaluator().evaluate(property_record(monthly_price=700_001), expected)
    assert failure_names(failure) == ["max_budget"]
    assert failure.failures[0].actual == 700_001


def test_currency_mismatch_cannot_be_compared_as_budget_match() -> None:
    result = ConstraintEvaluator().evaluate(
        property_record(currency="USD"),
        requirements(operation_type="rent", max_budget=700_000, currency="CLP"),
    )
    assert failure_names(result) == ["currency", "max_budget"]


def test_minimum_bedrooms_and_bathrooms_require_known_sufficient_values() -> None:
    expected = requirements(min_bedrooms=2, min_bathrooms=2)
    assert ConstraintEvaluator().evaluate(property_record(), expected).eligible
    unknown = ConstraintEvaluator().evaluate(property_record(bedrooms=None), expected)
    assert failure_names(unknown) == ["min_bedrooms"]
    insufficient = ConstraintEvaluator().evaluate(property_record(bathrooms=1), expected)
    assert failure_names(insufficient) == ["min_bathrooms"]


def test_required_parking_and_pets_fail_unknown_property_data() -> None:
    expected = requirements(parking_required=True, pets_required=True)
    result = ConstraintEvaluator().evaluate(
        property_record(parking_spaces=None, pet_policy="unknown"), expected
    )
    assert failure_names(result) == ["parking_required", "pets_required"]


def test_false_required_flags_are_not_prohibitions() -> None:
    expected = requirements(parking_required=False, pets_required=False)
    result = ConstraintEvaluator().evaluate(
        property_record(parking_spaces=None, pet_policy="unknown"), expected
    )
    assert result.eligible


def test_explicit_location_matches_city_sector_or_stable_combination() -> None:
    evaluator = ConstraintEvaluator()
    assert evaluator.evaluate(property_record(), requirements(locations=["Viña del Mar"])).eligible
    assert evaluator.evaluate(property_record(), requirements(locations=["Recreo"])).eligible
    assert evaluator.evaluate(
        property_record(), requirements(locations=["Recreo, Viña del Mar"])
    ).eligible
    excluded = evaluator.evaluate(property_record(), requirements(locations=["Concón"]))
    assert failure_names(excluded) == ["location"]


def test_operation_type_and_property_type_are_hard_constraints_when_explicit() -> None:
    expected = requirements(operation_type="buy", property_types=["house"])
    result = ConstraintEvaluator().evaluate(property_record(), expected)
    assert failure_names(result) == ["operation_type", "property_type"]


def test_multiple_constraints_report_every_exclusion_reason() -> None:
    expected = requirements(
        operation_type="rent",
        property_types=["apartment"],
        locations=["Concón"],
        max_budget=500_000,
        currency="CLP",
        min_bedrooms=3,
        min_bathrooms=3,
        parking_required=True,
        pets_required=True,
    )
    result = ConstraintEvaluator().evaluate(
        property_record(parking_spaces=None, pet_policy="unknown"), expected
    )
    assert failure_names(result) == [
        "location",
        "max_budget",
        "min_bedrooms",
        "min_bathrooms",
        "parking_required",
        "pets_required",
    ]


def test_grounded_soft_reasons_use_exact_normalized_tokens_not_substrings() -> None:
    expected = requirements(soft_preferences=["vista al mar"])
    false_positive = PropertyMatchingService._soft_reasons(
        property_record(description="Dormitorio con armario amplio."), expected
    )
    grounded = PropertyMatchingService._soft_reasons(
        property_record(description="Dormitorio con vista al mar."), expected
    )
    assert false_positive == []
    assert grounded == [
        {"preference": "vista al mar", "property_fact": "Dormitorio con vista al mar."}
    ]
