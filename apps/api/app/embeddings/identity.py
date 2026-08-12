import hashlib
from urllib.parse import urlsplit


def embedding_space_id(
    *,
    provider: str,
    model: str,
    dimension: int,
    endpoint: str | None = None,
) -> str:
    """Return a non-sensitive identity for one compatible vector space."""
    endpoint_identity = ""
    if endpoint:
        parsed = urlsplit(endpoint)
        host = (parsed.hostname or "").casefold()
        port = f":{parsed.port}" if parsed.port is not None else ""
        endpoint_identity = f"{parsed.scheme.casefold()}://{host}{port}{parsed.path.rstrip('/')}"
    material = "\n".join((provider, model, str(dimension), endpoint_identity))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()
