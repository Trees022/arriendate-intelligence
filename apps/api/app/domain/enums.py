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


class CommercialStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    RESERVED = "reserved"
    CLOSED = "closed"
    ARCHIVED = "archived"


class ChannelType(StrEnum):
    FACEBOOK_PAGE = "facebook_page"
    MESSENGER = "messenger"
    FACEBOOK_MARKETPLACE = "facebook_marketplace"
    FACEBOOK_GROUP = "facebook_group"
    INSTAGRAM_PROFESSIONAL = "instagram_professional"
    PORTAL_INMOBILIARIO = "portal_inmobiliario"
    YAPO = "yapo"
    WHATSAPP_CATALOG = "whatsapp_catalog"
    WHATSAPP = "whatsapp"
    WEBSITE = "website"
    EMAIL = "email"
    GENERIC = "generic"


class ExecutionMode(StrEnum):
    ASSISTED = "assisted"
    MANUAL = "manual"
    API = "api"
    LOCAL_AGENT = "local_agent"


class PackageStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    ARCHIVED = "archived"


class CampaignStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class JobStatus(StrEnum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    PUBLISHED = "published"
    FAILED = "failed"
    COOLDOWN = "cooldown"
    CANCELLED = "cancelled"


class ChannelProvider(StrEnum):
    META = "meta"
    ASSISTED = "assisted"
    WEBSITE = "website"
    WHATSAPP = "whatsapp"
    EMAIL = "email"


class AccountType(StrEnum):
    FACEBOOK_PAGE = "facebook_page"
    INSTAGRAM_PROFESSIONAL = "instagram_professional"


class ConnectionStatus(StrEnum):
    FIXTURE = "fixture"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    REQUIRES_ACTION = "requires_action"


class ChannelCapability(StrEnum):
    PUBLISH_CONTENT = "publish_content"
    READ_COMMENTS = "read_comments"
    REPLY_COMMENTS = "reply_comments"
    READ_MESSAGES = "read_messages"
    SEND_MESSAGES = "send_messages"
    READ_REACTIONS = "read_reactions"
    READ_METRICS = "read_metrics"
    SCHEDULE_CONTENT = "schedule_content"
    AUTOMATIC_REPOST = "automatic_repost"
    ASSISTED_PUBLISH = "assisted_publish"


class CapabilityAvailability(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    REQUIRES_PERMISSION = "requires_permission"
    REQUIRES_CONNECTION = "requires_connection"
    ASSISTED_ONLY = "assisted_only"


class ConversationStatus(StrEnum):
    OPEN = "open"
    NEEDS_REPLY = "needs_reply"
    HANDLED = "handled"
    ARCHIVED = "archived"


class MessageDirection(StrEnum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class ReplyStatus(StrEnum):
    NEW = "new"
    NEEDS_REPLY = "needs_reply"
    REPLIED = "replied"
    IGNORED = "ignored"
