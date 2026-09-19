from datetime import datetime
from typing import Any, Literal
from urllib.parse import urlparse
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.ai.property_autofill import PropertyAutofillDraft
from app.ai.schemas import (
    MissingInformation,
    RequestedCurrency,
    RequestedOperation,
    RequestedPropertyType,
)
from app.domain.capabilities import validate_execution_mode
from app.domain.enums import (
    AccountType,
    AvailabilityStatus,
    CampaignStatus,
    CapabilityAvailability,
    ChannelCapability,
    ChannelProvider,
    ChannelType,
    CommercialStatus,
    ConnectionStatus,
    ConversationStatus,
    ExecutionMode,
    JobStatus,
    LeadStatus,
    MessageDirection,
    OperationType,
    PackageStatus,
    PetPolicy,
    ReplyStatus,
)


def _validated_http_url(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("La URL debe usar http o https y contener un host")
    return normalized


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


class LeadListResponse(BaseModel):
    items: list[LeadResponse]
    total: int
    page: int
    page_size: int


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


class PropertyCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=3, max_length=180)
    description: str = Field(default="", max_length=10_000)
    operation_type: OperationType
    property_type: str = Field(min_length=2, max_length=40)
    city: str = Field(min_length=2, max_length=100)
    sector: str | None = Field(default=None, max_length=120)
    monthly_price: int | None = Field(default=None, ge=0)
    sale_price: int | None = Field(default=None, ge=0)
    currency: str = Field(default="CLP", max_length=3)
    bedrooms: int | None = Field(default=None, ge=0)
    bathrooms: int | None = Field(default=None, ge=0)
    parking_spaces: int | None = Field(default=None, ge=0)
    pet_policy: PetPolicy = PetPolicy.UNKNOWN
    furnished: bool | None = None
    square_meters: float | None = Field(default=None, gt=0)
    reference_code: str | None = Field(default=None, max_length=50)
    source_notes: str | None = Field(default=None, max_length=5_000)
    address_text: str | None = Field(default=None, max_length=250)
    built_area_m2: float | None = Field(default=None, gt=0)
    land_area_m2: float | None = Field(default=None, gt=0)
    commercial_status: CommercialStatus = CommercialStatus.DRAFT
    amenities: list[str] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def validate_operation_price_consistency(self) -> "PropertyCreate":
        if self.operation_type == OperationType.RENT:
            if self.monthly_price is None or self.sale_price is not None:
                raise ValueError("Para arriendo, debe especificar monthly_price y no sale_price")
        elif self.operation_type == OperationType.BUY:
            if self.sale_price is None or self.monthly_price is not None:
                raise ValueError("Para compra, debe especificar sale_price y no monthly_price")
        return self


class PropertyAutofillRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_text: str = Field(min_length=20, max_length=10_000)

    @field_validator("source_text")
    @classmethod
    def reject_blank_source_text(cls, value: str) -> str:
        if len(value.strip()) < 20:
            raise ValueError("La descripción debe contener al menos 20 caracteres útiles")
        return value


class PropertyAutofillResponse(BaseModel):
    draft: PropertyAutofillDraft
    filled_fields: list[str]
    review_fields: list[str]
    provider: str
    model: str


class PropertyUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=3, max_length=180)
    description: str | None = Field(default=None, max_length=10_000)
    operation_type: OperationType | None = None
    property_type: str | None = Field(default=None, min_length=2, max_length=40)
    city: str | None = Field(default=None, min_length=2, max_length=100)
    sector: str | None = Field(default=None, max_length=120)
    monthly_price: int | None = Field(default=None, ge=0)
    sale_price: int | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, max_length=3)
    bedrooms: int | None = Field(default=None, ge=0)
    bathrooms: int | None = Field(default=None, ge=0)
    parking_spaces: int | None = Field(default=None, ge=0)
    pet_policy: PetPolicy | None = None
    furnished: bool | None = None
    square_meters: float | None = Field(default=None, gt=0)
    reference_code: str | None = Field(default=None, max_length=50)
    source_notes: str | None = Field(default=None, max_length=5_000)
    address_text: str | None = Field(default=None, max_length=250)
    built_area_m2: float | None = Field(default=None, gt=0)
    land_area_m2: float | None = Field(default=None, gt=0)
    commercial_status: CommercialStatus | None = None
    availability_status: AvailabilityStatus | None = None
    amenities: list[str] | None = Field(default=None, max_length=50)


class PropertyMediaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    property_id: UUID
    storage_key: str
    original_filename: str
    media_type: str
    mime_type: str
    size_bytes: int
    position: int
    is_cover: bool
    url: str
    created_at: datetime


class PropertyMediaReorderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    media_ids: list[UUID]


class PropertyMediaUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_cover: bool | None = None
    position: int | None = Field(default=None, ge=0)


class PublicationPackageVariantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    package_id: UUID
    channel_type: ChannelType
    headline: str
    body: str
    short_body: str | None
    highlights: list[str]
    cta: str
    suggested_media_ids: list[UUID]
    warnings: list[str]
    created_at: datetime


class PublicationPackageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    property_id: UUID
    property_fingerprint: str
    status: PackageStatus
    variants: list[PublicationPackageVariantResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class PublicationTargetCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=150)
    channel_type: ChannelType
    execution_mode: ExecutionMode
    destination_url: str | None = Field(default=None, max_length=2_000)
    channel_account_id: UUID | None = None
    geographic_relevance: str | None = Field(default=None, max_length=160)
    property_tags: list[str] = Field(default_factory=list, max_length=30)
    active: bool = True
    minimum_repost_interval_hours: int = Field(default=72, ge=0)
    notes: str | None = Field(default=None, max_length=2_000)

    @field_validator("destination_url")
    @classmethod
    def validate_destination_url(cls, value: str | None) -> str | None:
        return _validated_http_url(value)

    @field_validator("property_tags")
    @classmethod
    def normalize_property_tags(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        for tag in value:
            clean = tag.strip()
            if not clean or len(clean) > 60:
                raise ValueError("Cada tag debe contener entre 1 y 60 caracteres")
            if clean not in normalized:
                normalized.append(clean)
        return normalized

    @model_validator(mode="after")
    def reject_unsupported_api_surfaces(self) -> "PublicationTargetCreate":
        try:
            validate_execution_mode(self.channel_type, self.execution_mode)
        except ValueError as error:
            raise ValueError(str(error)) from error
        return self


class PublicationTargetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    channel_type: ChannelType
    execution_mode: ExecutionMode
    destination_url: str | None
    channel_account_id: UUID | None
    geographic_relevance: str | None
    property_tags: list[str]
    active: bool
    minimum_repost_interval_hours: int
    notes: str | None
    is_demo: bool
    created_at: datetime
    updated_at: datetime


class CampaignCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    property_id: UUID
    package_id: UUID
    target_ids: list[UUID] = Field(min_length=1)


class PublicationJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    campaign_id: UUID
    campaign_target_id: UUID | None
    property_id: UUID
    target_id: UUID
    package_id: UUID
    variant_type: ChannelType
    execution_mode: ExecutionMode
    status: JobStatus
    scheduled_at: datetime
    next_eligible_at: datetime | None
    attempt_count: int
    error_code: str | None
    error_message: str | None
    action_required: bool
    action_note: str | None
    created_at: datetime
    updated_at: datetime


class PublicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_id: UUID | None
    property_id: UUID
    campaign_id: UUID
    target_id: UUID
    package_id: UUID
    channel_account_id: UUID | None
    variant_type: ChannelType
    external_publication_id: str | None
    published_at: datetime
    publication_url: str | None
    execution_mode: ExecutionMode
    created_at: datetime


class CampaignDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    property_id: UUID
    package_id: UUID
    status: CampaignStatus
    targets: list[PublicationTargetResponse] = Field(default_factory=list)
    jobs: list[PublicationJobResponse] = Field(default_factory=list)
    publications: list[PublicationResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class JobPublishRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    publication_url: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=300)

    @field_validator("publication_url")
    @classmethod
    def validate_publication_url(cls, value: str | None) -> str | None:
        return _validated_http_url(value)


class JobActionRequiredRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    note: str = Field(min_length=3, max_length=300)


class JobFailRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error_code: str = Field(default="assisted_failed", min_length=2, max_length=100)
    error_message: str = Field(min_length=3, max_length=300)


class ReconcileResponse(BaseModel):
    reconciled_jobs: int
    timestamp: datetime


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
    reference_code: str | None = None
    source_notes: str | None = None
    address_text: str | None = None
    built_area_m2: float | None = None
    land_area_m2: float | None = None
    commercial_status: CommercialStatus = CommercialStatus.DRAFT
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


class CapabilityStatusResponse(BaseModel):
    capability: ChannelCapability
    availability: CapabilityAvailability
    reason: str | None = None


class ChannelAccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    provider: ChannelProvider
    account_type: AccountType
    external_account_id: str
    display_name: str
    connection_status: ConnectionStatus
    capabilities: dict[str, str]
    is_demo: bool
    connected_at: datetime | None
    last_sync_at: datetime | None
    created_at: datetime
    updated_at: datetime


class EngagementSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    publication_id: UUID
    captured_at: datetime
    comments_count: int | None
    reactions_count: int | None
    views_count: int | None
    impressions_count: int | None
    messages_count: int | None
    source: str
    capability_version: str
    is_demo: bool


class PublicationCommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    publication_id: UUID
    external_comment_id: str
    author_display_name: str | None
    body: str
    created_external_at: datetime
    reply_status: ReplyStatus
    is_demo: bool


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    external_message_id: str
    direction: MessageDirection
    sender_display_name: str | None
    message_type: str
    body: str | None
    sent_at: datetime
    is_demo: bool


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    channel_account_id: UUID
    external_conversation_id: str
    channel_type: ChannelType
    property_id: UUID | None
    publication_id: UUID | None
    lead_id: UUID | None
    status: ConversationStatus
    last_message_at: datetime
    is_demo: bool
    messages: list[MessageResponse] = Field(default_factory=list)


class EngagementSummaryResponse(BaseModel):
    comments_count: int | None
    reactions_count: int | None
    views_count: int | None
    impressions_count: int | None
    messages_count: int | None
    last_captured_at: datetime | None


class PropertyActionResponse(BaseModel):
    type: str
    priority: Literal["high", "medium", "low"]
    title: str
    description: str
    related_entity_type: str | None = None
    related_entity_id: UUID | None = None


class DistributionItemResponse(BaseModel):
    target: PublicationTargetResponse
    job: PublicationJobResponse | None
    latest_publication: PublicationResponse | None
    package_variant: PublicationPackageVariantResponse | None
    prepared_media: list[PropertyMediaResponse] = Field(default_factory=list)
    status: str
    last_publication_at: datetime | None
    next_eligible_at: datetime | None
    publication_url: str | None
    action_required: bool
    capabilities: list[CapabilityStatusResponse]


class PropertyCommandCenterResponse(BaseModel):
    property: PropertyResponse
    demo_mode: bool
    channel_accounts: list[ChannelAccountResponse]
    distribution: list[DistributionItemResponse]
    engagement: EngagementSummaryResponse
    engagement_snapshots: list[EngagementSnapshotResponse]
    recent_comments: list[PublicationCommentResponse]
    related_conversations: list[ConversationResponse]
    next_actions: list[PropertyActionResponse]
    campaigns: list[CampaignDetailResponse]


class HealthResponse(BaseModel):
    status: str
    database: str


class ConstraintCheckResponse(BaseModel):
    constraint: str
    expected: Any
    actual: Any
    passed: bool


class SoftMatchReasonResponse(BaseModel):
    preference: str
    property_fact: str


class ExclusionSummaryResponse(BaseModel):
    constraint: str
    excluded_count: int


class PropertyMatchResponse(BaseModel):
    rank: int
    semantic_score: float | None
    hard_constraint_matches: list[ConstraintCheckResponse]
    soft_match_reasons: list[SoftMatchReasonResponse]
    property: PropertyResponse


class LeadMatchesResponse(BaseModel):
    status: Literal["not_run", "succeeded"]
    run_id: UUID | None
    algorithm_version: str | None
    embedding_provider: str | None
    embedding_model: str | None
    requested_top_k: int | None
    total_properties: int
    candidate_count: int
    result_count: int
    latency_ms: int | None
    embedding_latency_ms: int | None
    exclusion_summary: list[ExclusionSummaryResponse]
    items: list[PropertyMatchResponse]
    created_at: datetime | None
