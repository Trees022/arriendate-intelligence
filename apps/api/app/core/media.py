MAX_MEDIA_FILE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB
ALLOWED_MEDIA_MIME_TYPES: frozenset[str] = frozenset(
    {"image/jpeg", "image/png", "image/webp"}
)
ALLOWED_MEDIA_EXTENSIONS: frozenset[str] = frozenset(
    {".jpg", ".jpeg", ".png", ".webp"}
)
