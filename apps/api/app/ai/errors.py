class ProviderError(Exception):
    """Sanitized provider failure that never includes prompt or response bodies."""

    def __init__(self, *, code: str, message: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.safe_message = message
        self.retryable = retryable


class ProviderNotConfiguredError(ProviderError):
    def __init__(self) -> None:
        super().__init__(
            code="provider_not_configured",
            message="El proveedor de IA no está configurado en el servidor",
        )
