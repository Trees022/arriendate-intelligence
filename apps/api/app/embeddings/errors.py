class EmbeddingError(Exception):
    def __init__(self, code: str, safe_message: str, *, timeout: bool = False) -> None:
        super().__init__(safe_message)
        self.code = code
        self.safe_message = safe_message
        self.timeout = timeout


class EmbeddingNotConfiguredError(EmbeddingError):
    def __init__(self) -> None:
        super().__init__(
            "embedding_provider_not_configured",
            "El proveedor de embeddings no está configurado",
        )
