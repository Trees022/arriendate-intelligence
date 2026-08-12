class AppError(Exception):
    """Expected application error safe to expose through the HTTP boundary."""

    def __init__(self, *, status_code: int, code: str, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.code = code
        self.detail = detail


class NotFoundError(AppError):
    def __init__(self, detail: str) -> None:
        super().__init__(status_code=404, code="not_found", detail=detail)


class ConflictError(AppError):
    def __init__(self, detail: str) -> None:
        super().__init__(status_code=409, code="conflict", detail=detail)


class AIProviderUnavailableError(AppError):
    def __init__(self, detail: str, *, timeout: bool = False) -> None:
        super().__init__(
            status_code=504 if timeout else 503,
            code="ai_provider_timeout" if timeout else "ai_provider_unavailable",
            detail=detail,
        )


class AIProviderResponseError(AppError):
    def __init__(self, detail: str) -> None:
        super().__init__(status_code=502, code="ai_provider_response_error", detail=detail)


class InvalidAIOutputError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=502,
            code="invalid_ai_output",
            detail=(
                "El proveedor devolvió una extracción inválida. El lead original sigue "
                "guardado y no se aplicaron cambios."
            ),
        )


class EmbeddingProviderUnavailableError(AppError):
    def __init__(self, detail: str, *, timeout: bool = False) -> None:
        super().__init__(
            status_code=504 if timeout else 503,
            code="embedding_provider_timeout" if timeout else "embedding_provider_unavailable",
            detail=detail,
        )
