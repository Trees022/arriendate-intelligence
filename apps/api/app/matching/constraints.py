import unicodedata
from dataclasses import dataclass
from typing import Any

from app.db.models import LeadRequirement, Property


@dataclass(frozen=True, slots=True)
class ConstraintCheck:
    constraint: str
    expected: Any
    actual: Any
    passed: bool


@dataclass(frozen=True, slots=True)
class ConstraintEvaluation:
    eligible: bool
    checks: tuple[ConstraintCheck, ...]

    @property
    def failures(self) -> tuple[ConstraintCheck, ...]:
        return tuple(check for check in self.checks if not check.passed)


def normalize_location(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold().strip())
    return " ".join(
        "".join(character for character in decomposed if not unicodedata.combining(character))
        .replace(",", " ")
        .split()
    )


class ConstraintEvaluator:
    def evaluate(
        self, property_record: Property, requirements: LeadRequirement
    ) -> ConstraintEvaluation:
        checks: list[ConstraintCheck] = [
            self._check(
                "availability", "available", property_record.availability_status,
                property_record.availability_status == "available",
            )
        ]
        if requirements.operation_type != "unknown":
            checks.append(
                self._check(
                    "operation_type", requirements.operation_type,
                    property_record.operation_type,
                    property_record.operation_type == requirements.operation_type,
                )
            )
        if requirements.property_types:
            checks.append(
                self._check(
                    "property_type", requirements.property_types,
                    property_record.property_type,
                    property_record.property_type in requirements.property_types,
                )
            )
        if requirements.locations:
            actual_locations = {normalize_location(property_record.city)}
            if property_record.sector:
                actual_locations.update(
                    {
                        normalize_location(property_record.sector),
                        normalize_location(f"{property_record.city} {property_record.sector}"),
                        normalize_location(f"{property_record.sector} {property_record.city}"),
                    }
                )
            expected_locations = {normalize_location(value) for value in requirements.locations}
            checks.append(
                self._check(
                    "location", requirements.locations,
                    {"city": property_record.city, "sector": property_record.sector},
                    bool(actual_locations & expected_locations),
                )
            )
        if requirements.max_budget is not None:
            price = (
                property_record.monthly_price
                if requirements.operation_type == "rent"
                else property_record.sale_price
            )
            currency_matches = (
                requirements.currency is not None
                and property_record.currency == requirements.currency
            )
            checks.append(
                self._check(
                    "currency", requirements.currency or "known",
                    property_record.currency,
                    currency_matches,
                )
            )
            checks.append(
                self._check(
                    "max_budget", requirements.max_budget, price,
                    currency_matches and price is not None and price <= requirements.max_budget,
                )
            )
        if requirements.min_bedrooms is not None:
            checks.append(
                self._minimum("min_bedrooms", requirements.min_bedrooms, property_record.bedrooms)
            )
        if requirements.min_bathrooms is not None:
            checks.append(
                self._minimum(
                    "min_bathrooms", requirements.min_bathrooms, property_record.bathrooms
                )
            )
        if requirements.parking_required is True:
            checks.append(self._minimum("parking_required", 1, property_record.parking_spaces))
        if requirements.pets_required is True:
            checks.append(
                self._check(
                    "pets_required", "allowed", property_record.pet_policy,
                    property_record.pet_policy == "allowed",
                )
            )
        return ConstraintEvaluation(
            eligible=all(check.passed for check in checks),
            checks=tuple(checks),
        )

    @staticmethod
    def _minimum(constraint: str, expected: int, actual: int | None) -> ConstraintCheck:
        return ConstraintCheck(
            constraint=constraint,
            expected=expected,
            actual=actual,
            passed=actual is not None and actual >= expected,
        )

    @staticmethod
    def _check(constraint: str, expected: Any, actual: Any, passed: bool) -> ConstraintCheck:
        return ConstraintCheck(constraint, expected, actual, passed)
