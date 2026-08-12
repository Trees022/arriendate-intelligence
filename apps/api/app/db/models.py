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
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.domain.enums import AvailabilityStatus, LeadStatus, OperationType, PetPolicy

StringList = ARRAY(String()).with_variant(JSON(), "sqlite")


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
        Index("properties_inventory_idx", "availability_status", "operation_type", "city"),
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
