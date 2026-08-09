from enum import StrEnum


class LeadStatus(StrEnum):
    NEW = "new"
    QUALIFIED = "qualified"
    NEEDS_INFORMATION = "needs_information"
    MATCHED = "matched"
    CONTACTED = "contacted"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


class OperationType(StrEnum):
    RENT = "rent"
    BUY = "buy"


class AvailabilityStatus(StrEnum):
    AVAILABLE = "available"
    RESERVED = "reserved"
    UNAVAILABLE = "unavailable"


class PetPolicy(StrEnum):
    ALLOWED = "allowed"
    NOT_ALLOWED = "not_allowed"
    UNKNOWN = "unknown"
