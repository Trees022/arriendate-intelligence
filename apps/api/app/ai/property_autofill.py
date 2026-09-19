from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.ai.contracts import PromptMessage, StructuredGenerationRequest
from app.domain.enums import OperationType, PetPolicy

PROPERTY_AUTOFILL_PROMPT_VERSION = "property-autofill-v1.0.0"
PropertyDraftType = Literal[
    "house",
    "apartment",
    "land",
    "commercial",
    "office",
    "warehouse",
]


class PropertyAutofillDraft(BaseModel):
    """Facts explicitly present in operator-provided property text."""

    model_config = ConfigDict(extra="forbid")

    operation_type: OperationType | None = None
    property_type: PropertyDraftType | None = None
    title: str | None = Field(default=None, max_length=180)
    description: str | None = Field(default=None, max_length=10_000)
    price: int | None = Field(default=None, ge=0)
    currency: Literal["CLP", "UF", "USD"] | None = None
    city: str | None = Field(default=None, max_length=100)
    sector: str | None = Field(default=None, max_length=120)
    address_text: str | None = Field(default=None, max_length=250)
    bedrooms: int | None = Field(default=None, ge=0)
    bathrooms: int | None = Field(default=None, ge=0)
    parking_spaces: int | None = Field(default=None, ge=0)
    built_area_m2: float | None = Field(default=None, gt=0)
    land_area_m2: float | None = Field(default=None, gt=0)
    pet_policy: PetPolicy | None = None
    furnished: bool | None = None
    amenities: list[str] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def remove_fields_irrelevant_to_property_type(self) -> "PropertyAutofillDraft":
        if self.property_type == "land":
            self.bedrooms = None
            self.bathrooms = None
            self.built_area_m2 = None
            self.pet_policy = None
            self.furnished = None
        elif self.property_type == "apartment":
            self.land_area_m2 = None
        elif self.property_type in {"commercial", "office", "warehouse"}:
            self.bedrooms = None
            self.bathrooms = None
            self.pet_policy = None
            self.furnished = None
            if self.property_type != "warehouse":
                self.land_area_m2 = None
        return self


def build_property_autofill_request(source_text: str) -> StructuredGenerationRequest:
    instructions = """Extract property facts from the operator's text into the schema.

Rules:
- Use only facts explicitly stated in the source text.
- Never guess, infer, calculate or complete missing facts.
- Return null for every unknown scalar fact and [] when no amenities are explicitly stated.
- Map arriendo/alquiler to rent and venta to buy.
- Map parcela, lote and terreno to land; bodega/galpón to warehouse.
- Prices must be integer amounts with separators and currency symbols removed.
- Areas are numeric square metres only when the text states them.
- Do not turn promotional adjectives into factual amenities.
- Only extract title when the text contains a clear title, heading or reference; do not compose one.
- Keep the original factual description concise and do not add marketing claims.
- Property type determines relevant facts: land has no bedrooms, bathrooms or built area.
- Apartment has no land area. Commercial, office and warehouse have no residential-only facts.
"""
    return StructuredGenerationRequest(
        messages=(
            PromptMessage(role="developer", content=instructions),
            PromptMessage(role="user", content=source_text),
        ),
        schema_name="property_autofill_draft",
        schema=PropertyAutofillDraft.model_json_schema(),
    )
