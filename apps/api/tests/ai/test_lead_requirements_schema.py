import json
from collections.abc import Callable
from typing import Any

import pytest
from pydantic import ValidationError

from app.ai.schemas import LeadRequirements, MissingInformation, RequestedOperation
from tests.factories import VALID_REQUIREMENTS


def test_valid_complete_output_is_accepted() -> None:
    requirements = LeadRequirements.model_validate(VALID_REQUIREMENTS)

    assert requirements.operation_type is RequestedOperation.RENT
    assert requirements.max_budget == 700_000
    assert requirements.missing_information == []


@pytest.mark.parametrize(
    ("mutator", "expected_error"),
    [
        (lambda value: value.pop("confidence"), "Field required"),
        (lambda value: value.update({"max_budget": "700000"}), "Input should be a valid integer"),
        (lambda value: value.update({"invented_field": True}), "Extra inputs are not permitted"),
        (lambda value: value.update({"confidence": 1.4}), "less than or equal to 1"),
    ],
)
def test_malformed_or_incomplete_output_is_rejected(
    mutator: Callable[[dict[str, Any]], object], expected_error: str
) -> None:
    payload = dict(VALID_REQUIREMENTS)
    mutator(payload)

    with pytest.raises(ValidationError) as captured:
        LeadRequirements.model_validate(payload)

    assert expected_error in str(captured.value)


def test_structurally_valid_unknowns_require_missing_markers() -> None:
    payload = {
        **VALID_REQUIREMENTS,
        "operation_type": "unknown",
        "locations": [],
        "max_budget": None,
        "currency": None,
        "missing_information": [],
    }

    with pytest.raises(ValidationError) as captured:
        LeadRequirements.model_validate(payload)

    message = str(captured.value)
    assert MissingInformation.OPERATION_TYPE.value in message
    assert MissingInformation.LOCATION.value in message
    assert MissingInformation.BUDGET.value in message


def test_truncated_json_is_rejected() -> None:
    with pytest.raises(ValidationError):
        LeadRequirements.model_validate_json(json.dumps(VALID_REQUIREMENTS)[:-8])
