from enum import StrEnum
from typing import Annotated, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    field_validator,
    model_validator,
)

ShortText = Annotated[str, Field(min_length=1, max_length=160)]
NonNegativeInt = Annotated[StrictInt, Field(ge=0, le=2_147_483_647)]
SmallNonNegativeInt = Annotated[StrictInt, Field(ge=0, le=30)]


class RequestedOperation(StrEnum):
    RENT = "rent"
    BUY = "buy"
    UNKNOWN = "unknown"


class RequestedPropertyType(StrEnum):
    APARTMENT = "apartment"
    HOUSE = "house"
    STUDIO = "studio"
    LOFT = "loft"
    TOWNHOUSE = "townhouse"
    LAND = "land"
    COMMERCIAL = "commercial"
    OFFICE = "office"


class RequestedCurrency(StrEnum):
    CLP = "CLP"
    UF = "UF"
    USD = "USD"


class MissingInformation(StrEnum):
    OPERATION_TYPE = "operation_type"
    PROPERTY_TYPE = "property_type"
    LOCATION = "location"
    BUDGET = "budget"
    CURRENCY = "currency"
    BEDROOMS = "bedrooms"
    BATHROOMS = "bathrooms"
    PARKING = "parking"
    PETS = "pets"
    FURNISHED = "furnished"
    CONTRADICTORY_REQUIREMENTS = "contradictory_requirements"
    UNVERIFIABLE_PREFERENCE = "unverifiable_preference"


class LeadRequirements(BaseModel):
    """Strict machine output for one unstructured real-estate request."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        use_enum_values=False,
    )

    operation_type: RequestedOperation
    property_types: Annotated[list[RequestedPropertyType], Field(max_length=8)]
    locations: Annotated[list[ShortText], Field(max_length=12)]
    max_budget: NonNegativeInt | None
    currency: RequestedCurrency | None
    min_bedrooms: SmallNonNegativeInt | None
    min_bathrooms: SmallNonNegativeInt | None
    parking_required: StrictBool | None
    pets_required: StrictBool | None
    furnished_preference: StrictBool | None
    soft_preferences: Annotated[list[ShortText], Field(max_length=20)]
    missing_information: Annotated[list[MissingInformation], Field(max_length=12)]
    confidence: Annotated[float, Field(ge=0, le=1)]

    @field_validator("locations", "soft_preferences")
    @classmethod
    def reject_duplicate_text_items(cls, values: list[str]) -> list[str]:
        normalized = [value.casefold() for value in values]
        if len(normalized) != len(set(normalized)):
            raise ValueError("duplicate list items are not allowed")
        return values

    @field_validator("property_types", "missing_information")
    @classmethod
    def reject_duplicate_enum_items(cls, values: list[object]) -> list[object]:
        if len(values) != len(set(values)):
            raise ValueError("duplicate list items are not allowed")
        return values

    @model_validator(mode="after")
    def validate_missing_information_consistency(self) -> Self:
        missing = set(self.missing_information)
        required_markers: list[tuple[bool, MissingInformation]] = [
            (
                self.operation_type is RequestedOperation.UNKNOWN,
                MissingInformation.OPERATION_TYPE,
            ),
            (not self.property_types, MissingInformation.PROPERTY_TYPE),
            (not self.locations, MissingInformation.LOCATION),
            (self.max_budget is None, MissingInformation.BUDGET),
            (
                self.max_budget is not None and self.currency is None,
                MissingInformation.CURRENCY,
            ),
        ]
        absent_markers = [
            marker.value
            for required, marker in required_markers
            if required and marker not in missing
        ]
        if absent_markers:
            raise ValueError("missing_information must include: " + ", ".join(absent_markers))
        return self
