from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator, Uuid

from app.domain.enums import (
    AvailabilityStatus,
    CampaignStatus,
    CommercialStatus,
    JobStatus,
    LeadStatus,
    OperationType,
    PackageStatus,
    PetPolicy,
)

StringList = ARRAY(String()).with_variant(JSON(), "sqlite")
StringMap = JSON


class UuidListType(TypeDecorator[list[UUID]]):
    """Persist UUID arrays natively in Postgres and portably in SQLite."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect):  # type: ignore[no-untyped-def]
        if dialect.name == "postgresql":
            return dialect.type_descriptor(ARRAY(Uuid(as_uuid=True)))
        return dialect.type_descriptor(JSON())

    def process_bind_param(
        self, value: list[UUID] | None, dialect: Dialect
    ) -> list[UUID] | list[str] | None:
        if value is None or dialect.name == "postgresql":
            return value
        return [str(item) for item in value]

    def process_result_value(
        self, value: list[UUID] | list[str] | None, dialect: Dialect
    ) -> list[UUID]:
        del dialect
        return [item if isinstance(item, UUID) else UUID(item) for item in value or []]


UuidList = UuidListType()


class Base(DeclarativeBase):
    pass


class Lead(Base):
    __tablename__ = "leads"
    __table_args__ = (
        CheckConstraint(
            "length(original_request) BETWEEN 10 AND 10000", name="lead_request_length"
        ),
        CheckConstraint(
            "status IN ('new','qualified','needs_information','matched','contacted',"
            "'closed_won','closed_lost')",
            name="lead_status_allowed",
        ),
        UniqueConstraint("idempotency_key", name="leads_idempotency_key_key"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    original_request: Mapped[str] = mapped_column(Text, nullable=False)
    idempotency_key: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=LeadStatus.NEW.value, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Property(Base):
    __tablename__ = "properties"
    __table_args__ = (
        CheckConstraint("operation_type IN ('rent','buy')", name="property_operation_allowed"),
        CheckConstraint(
            "availability_status IN ('available','reserved','unavailable')",
            name="property_availability_allowed",
        ),
        CheckConstraint(
            "pet_policy IN ('allowed','not_allowed','unknown')",
            name="property_pet_policy_allowed",
        ),
        CheckConstraint(
            "monthly_price IS NULL OR monthly_price >= 0", name="monthly_price_positive"
        ),
        CheckConstraint("sale_price IS NULL OR sale_price >= 0", name="sale_price_positive"),
        CheckConstraint(
            "(operation_type = 'rent' AND monthly_price IS NOT NULL AND sale_price IS NULL) OR "
            "(operation_type = 'buy' AND sale_price IS NOT NULL AND monthly_price IS NULL)",
            name="property_operation_price_consistent",
        ),
        CheckConstraint(
            "commercial_status IN ('draft','active','reserved','closed','archived')",
            name="property_commercial_status_allowed",
        ),
        CheckConstraint(
            "length(description) BETWEEN 5 AND 10000",
            name="property_description_length",
        ),
        CheckConstraint(
            "source_notes IS NULL OR length(source_notes) <= 5000",
            name="property_source_notes_length",
        ),
        Index("properties_inventory_idx", "availability_status", "operation_type", "city"),
        Index("properties_commercial_status_idx", "commercial_status", "city"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    operation_type: Mapped[str] = mapped_column(String(12), nullable=False)
    property_type: Mapped[str] = mapped_column(String(40), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    sector: Mapped[str | None] = mapped_column(String(120), nullable=True)
    monthly_price: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    sale_price: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="CLP", nullable=False)
    bedrooms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bathrooms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    parking_spaces: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pet_policy: Mapped[str] = mapped_column(
        String(20), default=PetPolicy.UNKNOWN.value, nullable=False
    )
    furnished: Mapped[bool | None] = mapped_column(nullable=True)
    square_meters: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    reference_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    address_text: Mapped[str | None] = mapped_column(String(250), nullable=True)
    built_area_m2: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    land_area_m2: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    commercial_status: Mapped[str] = mapped_column(
        String(20), default=CommercialStatus.DRAFT.value, nullable=False
    )
    amenities: Mapped[list[str]] = mapped_column(StringList, default=list, nullable=False)
    availability_status: Mapped[str] = mapped_column(
        String(20), default=AvailabilityStatus.AVAILABLE.value, nullable=False
    )
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    embedding_provider: Mapped[str | None] = mapped_column(String(80), nullable=True)
    embedding_space_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    embedding_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    @property
    def price(self) -> int:
        if self.operation_type == OperationType.RENT.value:
            assert self.monthly_price is not None
            return self.monthly_price
        assert self.sale_price is not None
        return self.sale_price


class LeadRequirement(Base):
    __tablename__ = "lead_requirements"
    __table_args__ = (
        CheckConstraint(
            "operation_type IN ('rent','buy','unknown')",
            name="lead_requirement_operation_allowed",
        ),
        CheckConstraint(
            "extraction_confidence >= 0 AND extraction_confidence <= 1",
            name="lead_requirement_confidence_range",
        ),
        UniqueConstraint("lead_id", name="lead_requirements_lead_id_key"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    lead_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
    )
    operation_type: Mapped[str] = mapped_column(String(12), nullable=False)
    property_types: Mapped[list[str]] = mapped_column(StringList, default=list, nullable=False)
    locations: Mapped[list[str]] = mapped_column(StringList, default=list, nullable=False)
    max_budget: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    min_bedrooms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    min_bathrooms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    parking_required: Mapped[bool | None] = mapped_column(nullable=True)
    pets_required: Mapped[bool | None] = mapped_column(nullable=True)
    furnished_preference: Mapped[bool | None] = mapped_column(nullable=True)
    soft_preferences: Mapped[list[str]] = mapped_column(StringList, default=list, nullable=False)
    missing_information: Mapped[list[str]] = mapped_column(StringList, default=list, nullable=False)
    extraction_confidence: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)
    extraction_model: Mapped[str] = mapped_column(String(120), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class AIRun(Base):
    __tablename__ = "ai_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('running','succeeded','failed')",
            name="ai_run_status_allowed",
        ),
        CheckConstraint("latency_ms >= 0", name="ai_run_latency_positive"),
        Index("ai_runs_lead_created_idx", "lead_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    run_type: Mapped[str] = mapped_column(String(40), nullable=False)
    lead_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=True,
    )
    property_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("properties.id", ondelete="SET NULL"),
        nullable=True,
    )
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    prompt_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    provider_request_id: Mapped[str | None] = mapped_column(String(180), nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 8), nullable=True)
    validation_passed: Mapped[bool] = mapped_column(default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="running", nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class MatchingRun(Base):
    __tablename__ = "matching_runs"
    __table_args__ = (
        CheckConstraint("requested_top_k BETWEEN 1 AND 10", name="matching_top_k_range"),
        CheckConstraint(
            "status IN ('running','succeeded','failed')", name="matching_status_allowed"
        ),
        CheckConstraint(
            "candidate_count <= total_properties AND result_count <= candidate_count "
            "AND result_count <= requested_top_k",
            name="matching_count_consistency",
        ),
        CheckConstraint(
            "(status = 'running' AND result_count = 0 AND error_code IS NULL "
            "AND error_message IS NULL) OR "
            "(status = 'succeeded' AND error_code IS NULL AND error_message IS NULL) OR "
            "(status = 'failed' AND result_count = 0 AND error_code IS NOT NULL "
            "AND error_message IS NOT NULL)",
            name="matching_status_consistency",
        ),
        CheckConstraint(
            "length(requirements_fingerprint) = 64", name="matching_fingerprint_length"
        ),
        CheckConstraint("length(embedding_space_id) = 64", name="matching_space_id_length"),
        UniqueConstraint("id", "lead_id", name="matching_runs_id_lead_key"),
        Index("matching_runs_lead_created_idx", "lead_id", "created_at"),
        Index("matching_runs_current_lead_idx", "lead_id", "invalidated_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    lead_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    algorithm_version: Mapped[str] = mapped_column(String(80), nullable=False)
    embedding_space_id: Mapped[str] = mapped_column(String(64), nullable=False)
    requirements_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    requested_top_k: Mapped[int] = mapped_column(Integer, nullable=False)
    total_properties: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    candidate_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    result_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    embedding_latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="running", nullable=False)
    exclusion_summary: Mapped[list[dict[str, object]]] = mapped_column(
        JSON, default=list, nullable=False
    )
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(300), nullable=True)
    invalidated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class PropertyMatch(Base):
    __tablename__ = "property_matches"
    __table_args__ = (
        UniqueConstraint("run_id", "property_id", name="property_matches_run_property_key"),
        UniqueConstraint("run_id", "rank", name="property_matches_run_rank_key"),
        ForeignKeyConstraint(
            ("run_id", "lead_id"),
            ("matching_runs.id", "matching_runs.lead_id"),
            ondelete="CASCADE",
            name="property_matches_run_lead_fkey",
        ),
        Index("property_matches_run_rank_idx", "run_id", "rank"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    lead_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False
    )
    property_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("properties.id", ondelete="RESTRICT"), nullable=False
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    semantic_score: Mapped[float | None] = mapped_column(Numeric(6, 5), nullable=True)
    hard_constraint_matches: Mapped[list[dict[str, object]]] = mapped_column(
        JSON, default=list, nullable=False
    )
    soft_match_reasons: Mapped[list[dict[str, str]]] = mapped_column(
        JSON, default=list, nullable=False
    )
    algorithm_version: Mapped[str] = mapped_column(String(80), nullable=False)
    embedding_model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ChannelAccount(Base):
    __tablename__ = "channel_accounts"
    __table_args__ = (
        CheckConstraint(
            "provider IN ('meta','assisted','website','whatsapp','email')",
            name="channel_account_provider_allowed",
        ),
        CheckConstraint(
            "account_type IN ('facebook_page','instagram_professional')",
            name="channel_account_type_allowed",
        ),
        CheckConstraint(
            "connection_status IN ('fixture','connected','disconnected','requires_action')",
            name="channel_account_connection_status_allowed",
        ),
        UniqueConstraint(
            "provider", "external_account_id", name="uq_channel_account_external_scope"
        ),
        Index("channel_accounts_status_idx", "connection_status", "account_type"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    provider: Mapped[str] = mapped_column(String(30), nullable=False)
    account_type: Mapped[str] = mapped_column(String(40), nullable=False)
    external_account_id: Mapped[str] = mapped_column(String(160), nullable=False)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    connection_status: Mapped[str] = mapped_column(String(30), nullable=False)
    capabilities: Mapped[dict[str, str]] = mapped_column(StringMap, default=dict, nullable=False)
    is_demo: Mapped[bool] = mapped_column(default=False, nullable=False)
    connected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class PropertyMedia(Base):
    __tablename__ = "property_media"
    __table_args__ = (
        CheckConstraint("media_type IN ('image')", name="media_type_allowed"),
        CheckConstraint(
            "mime_type IN ('image/jpeg','image/png','image/webp')", name="mime_type_allowed"
        ),
        CheckConstraint(
            "size_bytes > 0 AND size_bytes <= 10485760", name="media_size_bytes_limit"
        ),
        CheckConstraint("position >= 0", name="media_position_non_negative"),
        Index("property_media_property_pos_idx", "property_id", "position"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    property_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False
    )
    storage_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    media_type: Mapped[str] = mapped_column(String(20), default="image", nullable=False)
    mime_type: Mapped[str] = mapped_column(String(40), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_cover: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class PublicationPackage(Base):
    __tablename__ = "publication_packages"
    __table_args__ = (
        CheckConstraint("status IN ('draft','approved','archived')", name="package_status_allowed"),
        Index("publication_packages_property_idx", "property_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    property_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False
    )
    property_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default=PackageStatus.DRAFT.value, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class PublicationPackageVariant(Base):
    __tablename__ = "publication_package_variants"
    __table_args__ = (
        CheckConstraint(
            "channel_type IN ('facebook_page','facebook_marketplace','facebook_group',"
            "'instagram_professional','portal_inmobiliario','yapo','whatsapp_catalog',"
            "'website','email','generic')",
            name="variant_channel_type_allowed",
        ),
        UniqueConstraint("package_id", "channel_type", name="uq_package_channel"),
        CheckConstraint("length(headline) <= 500", name="variant_headline_length"),
        CheckConstraint("length(body) <= 20000", name="variant_body_length"),
        CheckConstraint(
            "short_body IS NULL OR length(short_body) <= 2000",
            name="variant_short_body_length",
        ),
        CheckConstraint("length(cta) <= 1000", name="variant_cta_length"),
        Index("package_variants_package_idx", "package_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    package_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("publication_packages.id", ondelete="CASCADE"),
        nullable=False,
    )
    channel_type: Mapped[str] = mapped_column(String(40), nullable=False)
    headline: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    short_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    highlights: Mapped[list[str]] = mapped_column(StringList, default=list, nullable=False)
    cta: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_media_ids: Mapped[list[UUID]] = mapped_column(UuidList, default=list, nullable=False)
    warnings: Mapped[list[str]] = mapped_column(StringList, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class PublicationTarget(Base):
    __tablename__ = "publication_targets"
    __table_args__ = (
        CheckConstraint(
            "channel_type IN ('facebook_page','facebook_marketplace','facebook_group',"
            "'instagram_professional','portal_inmobiliario','yapo','whatsapp_catalog',"
            "'website','email','generic')",
            name="target_channel_type_allowed",
        ),
        CheckConstraint(
            "execution_mode IN ('assisted','manual','api','local_agent')",
            name="target_execution_mode_allowed",
        ),
        CheckConstraint(
            "minimum_repost_interval_hours >= 0", name="target_min_interval_non_negative"
        ),
        CheckConstraint(
            "NOT (channel_type IN ('facebook_group','facebook_marketplace') "
            "AND execution_mode = 'api')",
            name="target_assisted_surface_not_api",
        ),
        CheckConstraint(
            "destination_url IS NULL OR length(destination_url) <= 2000",
            name="target_destination_url_length",
        ),
        CheckConstraint(
            "notes IS NULL OR length(notes) <= 2000",
            name="target_notes_length",
        ),
        Index("publication_targets_active_channel_idx", "active", "channel_type"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    channel_type: Mapped[str] = mapped_column(String(40), nullable=False)
    execution_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    channel_account_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("channel_accounts.id", ondelete="SET NULL"),
        nullable=True,
    )
    destination_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    geographic_relevance: Mapped[str | None] = mapped_column(String(160), nullable=True)
    property_tags: Mapped[list[str]] = mapped_column(StringList, default=list, nullable=False)
    active: Mapped[bool] = mapped_column(default=True, nullable=False)
    minimum_repost_interval_hours: Mapped[int] = mapped_column(Integer, default=72, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_demo: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Campaign(Base):
    __tablename__ = "campaigns"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft','active','paused','completed','archived')",
            name="campaign_status_allowed",
        ),
        Index("campaigns_property_status_idx", "property_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    property_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False
    )
    package_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("publication_packages.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20), default=CampaignStatus.DRAFT.value, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class CampaignTarget(Base):
    __tablename__ = "campaign_targets"
    __table_args__ = (
        UniqueConstraint("campaign_id", "target_id", name="uq_campaign_target"),
        Index("campaign_targets_campaign_idx", "campaign_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    campaign_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False
    )
    target_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("publication_targets.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class PublicationJob(Base):
    __tablename__ = "publication_jobs"
    __table_args__ = (
        CheckConstraint(
            "variant_type IN ('facebook_page','facebook_marketplace','facebook_group',"
            "'instagram_professional','portal_inmobiliario','yapo','whatsapp_catalog',"
            "'website','email','generic')",
            name="job_variant_type_allowed",
        ),
        CheckConstraint(
            "execution_mode IN ('assisted','manual','api','local_agent')",
            name="job_execution_mode_allowed",
        ),
        CheckConstraint(
            "status IN ('pending','ready','running','published','failed','cooldown','cancelled')",
            name="job_status_allowed",
        ),
        CheckConstraint("attempt_count >= 0", name="job_attempt_count_non_negative"),
        CheckConstraint(
            "error_message IS NULL OR length(error_message) <= 300",
            name="job_error_message_length",
        ),
        Index("publication_jobs_status_cooldown_idx", "status", "next_eligible_at"),
        Index("publication_jobs_property_target_idx", "property_id", "target_id"),
        Index("publication_jobs_campaign_idx", "campaign_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    campaign_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False
    )
    campaign_target_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("campaign_targets.id", ondelete="SET NULL"), nullable=True
    )
    property_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False
    )
    target_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("publication_targets.id", ondelete="CASCADE"),
        nullable=False,
    )
    package_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("publication_packages.id", ondelete="CASCADE"),
        nullable=False,
    )
    variant_type: Mapped[str] = mapped_column(String(40), nullable=False)
    execution_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default=JobStatus.PENDING.value, nullable=False
    )
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    next_eligible_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    action_required: Mapped[bool] = mapped_column(default=False, nullable=False)
    action_note: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Publication(Base):
    __tablename__ = "publications"
    __table_args__ = (
        CheckConstraint(
            "variant_type IN ('facebook_page','facebook_marketplace','facebook_group',"
            "'instagram_professional','portal_inmobiliario','yapo','whatsapp_catalog',"
            "'website','email','generic')",
            name="publication_variant_type_allowed",
        ),
        CheckConstraint(
            "execution_mode IN ('assisted','manual','api','local_agent')",
            name="publication_execution_mode_allowed",
        ),
        CheckConstraint(
            "publication_url IS NULL OR length(publication_url) <= 2000",
            name="publication_url_length",
        ),
        Index("publications_property_published_idx", "property_id", "published_at"),
        Index("publications_campaign_idx", "campaign_id"),
        UniqueConstraint(
            "channel_account_id",
            "external_publication_id",
            name="uq_publication_external_scope",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    job_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("publication_jobs.id", ondelete="SET NULL"), nullable=True
    )
    property_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False
    )
    campaign_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False
    )
    target_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("publication_targets.id", ondelete="CASCADE"),
        nullable=False,
    )
    package_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("publication_packages.id", ondelete="CASCADE"),
        nullable=False,
    )
    channel_account_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("channel_accounts.id", ondelete="SET NULL"),
        nullable=True,
    )
    variant_type: Mapped[str] = mapped_column(String(40), nullable=False)
    external_publication_id: Mapped[str | None] = mapped_column(String(180), nullable=True)
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    publication_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    execution_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class EngagementSnapshot(Base):
    __tablename__ = "engagement_snapshots"
    __table_args__ = (
        CheckConstraint(
            "comments_count IS NULL OR comments_count >= 0",
            name="engagement_comments_non_negative",
        ),
        CheckConstraint(
            "reactions_count IS NULL OR reactions_count >= 0",
            name="engagement_reactions_non_negative",
        ),
        CheckConstraint(
            "views_count IS NULL OR views_count >= 0",
            name="engagement_views_non_negative",
        ),
        CheckConstraint(
            "impressions_count IS NULL OR impressions_count >= 0",
            name="engagement_impressions_non_negative",
        ),
        CheckConstraint(
            "messages_count IS NULL OR messages_count >= 0",
            name="engagement_messages_non_negative",
        ),
        UniqueConstraint("publication_id", "captured_at", name="uq_engagement_capture"),
        Index("engagement_publication_captured_idx", "publication_id", "captured_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    publication_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("publications.id", ondelete="CASCADE"), nullable=False
    )
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    comments_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reactions_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    views_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    impressions_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    messages_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String(40), nullable=False)
    capability_version: Mapped[str] = mapped_column(String(40), default="v1", nullable=False)
    is_demo: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class PublicationComment(Base):
    __tablename__ = "publication_comments"
    __table_args__ = (
        CheckConstraint(
            "reply_status IN ('new','needs_reply','replied','ignored')",
            name="comment_reply_status_allowed",
        ),
        UniqueConstraint(
            "publication_id", "external_comment_id", name="uq_comment_external_scope"
        ),
        Index("comments_publication_created_idx", "publication_id", "created_external_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    publication_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("publications.id", ondelete="CASCADE"), nullable=False
    )
    external_comment_id: Mapped[str] = mapped_column(String(180), nullable=False)
    author_external_id: Mapped[str | None] = mapped_column(String(180), nullable=True)
    author_display_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    body: Mapped[str] = mapped_column(String(4000), nullable=False)
    created_external_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reply_status: Mapped[str] = mapped_column(String(20), nullable=False)
    is_demo: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        CheckConstraint(
            "channel_type IN ('messenger','instagram_professional','website','whatsapp','email')",
            name="conversation_channel_type_allowed",
        ),
        CheckConstraint(
            "status IN ('open','needs_reply','handled','archived')",
            name="conversation_status_allowed",
        ),
        UniqueConstraint(
            "channel_account_id",
            "external_conversation_id",
            name="uq_conversation_external_scope",
        ),
        Index("conversations_property_last_message_idx", "property_id", "last_message_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    channel_account_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("channel_accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    external_conversation_id: Mapped[str] = mapped_column(String(180), nullable=False)
    channel_type: Mapped[str] = mapped_column(String(40), nullable=False)
    property_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("properties.id", ondelete="SET NULL"), nullable=True
    )
    publication_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("publications.id", ondelete="SET NULL"), nullable=True
    )
    lead_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("leads.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    last_message_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_demo: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint(
            "direction IN ('inbound','outbound')", name="message_direction_allowed"
        ),
        UniqueConstraint(
            "conversation_id", "external_message_id", name="uq_message_external_scope"
        ),
        Index("messages_conversation_sent_idx", "conversation_id", "sent_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    conversation_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    external_message_id: Mapped[str] = mapped_column(String(180), nullable=False)
    direction: Mapped[str] = mapped_column(String(20), nullable=False)
    sender_external_id: Mapped[str | None] = mapped_column(String(180), nullable=True)
    sender_display_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    message_type: Mapped[str] = mapped_column(String(30), default="text", nullable=False)
    body: Mapped[str | None] = mapped_column(String(10000), nullable=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_demo: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
