from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    BigInteger,
    CheckConstraint,
    DateTime,
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
