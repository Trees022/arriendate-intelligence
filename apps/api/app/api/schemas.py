from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.ai.schemas import (
    MissingInformation,
    RequestedCurrency,
    RequestedOperation,
    RequestedPropertyType,
)
from app.domain.enums import AvailabilityStatus, LeadStatus, OperationType, PetPolicy


class LeadCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, max_length=120)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)
    original_request: str = Field(min_length=10, max_length=10_000)

    @field_validator("name", "phone")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("original_request")
    @classmethod
    def reject_blank_request_without_rewriting(cls, value: str) -> str:
        if len(value.strip()) < 10:
            raise ValueError("La solicitud debe contener al menos 10 caracteres útiles")
        return value


class LeadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str | None
    email: str | None
    phone: str | None
    original_request: str
    status: LeadStatus
    created_at: datetime
    updated_at: datetime


class LeadRequirementsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    operation_type: RequestedOperation
    property_types: list[RequestedPropertyType]
    locations: list[str]
    max_budget: int | None
    currency: RequestedCurrency | None
    min_bedrooms: int | None
    min_bathrooms: int | None
    parking_required: bool | None
    pets_required: bool | None
    furnished_preference: bool | None
    soft_preferences: list[str]
    missing_information: list[MissingInformation]
    extraction_confidence: float
    extraction_model: str
    prompt_version: str
    created_at: datetime
    updated_at: datetime


class AIRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    run_type: str
    provider: str
    model: str
    prompt_version: str | None
    provider_request_id: str | None
    latency_ms: int
    input_tokens: int | None
    output_tokens: int | None
    estimated_cost: float | None
    validation_passed: bool
    status: str
    error_code: str | None
    error_message: str | None
    created_at: datetime


class LeadDetailResponse(LeadResponse):
    requirements: LeadRequirementsResponse | None
    ai_runs: list[AIRunResponse]


class LeadExtractionResponse(BaseModel):
    lead_status: LeadStatus
    requirements: LeadRequirementsResponse
    ai_run: AIRunResponse


class PropertyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str
    operation_type: OperationType
    property_type: str
    city: str
    sector: str | None
    monthly_price: int | None
    sale_price: int | None
    currency: str
    bedrooms: int | None
    bathrooms: int | None
    parking_spaces: int | None
    pet_policy: PetPolicy
    furnished: bool | None
    square_meters: float | None
    amenities: list[str]
    availability_status: AvailabilityStatus
    source_text: str
    created_at: datetime
    updated_at: datetime


class PropertyListResponse(BaseModel):
    items: list[PropertyResponse]
    total: int
    page: int
    page_size: int


class HealthResponse(BaseModel):
    status: str
    database: str
