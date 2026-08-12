import hashlib
import json

from app.db.models import LeadRequirement

MATCHING_REQUIREMENT_FIELDS = (
    "operation_type",
    "property_types",
    "locations",
    "max_budget",
    "currency",
    "min_bedrooms",
    "min_bathrooms",
    "parking_required",
    "pets_required",
    "furnished_preference",
    "soft_preferences",
)


def requirements_fingerprint(requirements: LeadRequirement) -> str:
    payload = {
        field: getattr(requirements, field) for field in MATCHING_REQUIREMENT_FIELDS
    }
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def matching_requirements_error(requirements: LeadRequirement) -> str | None:
    if requirements.max_budget is None:
        return None
    if requirements.operation_type == "unknown":
        return "El tipo de operación debe estar definido para interpretar el presupuesto"
    if requirements.currency is None:
        return "La moneda debe estar definida para interpretar el presupuesto"
    return None
