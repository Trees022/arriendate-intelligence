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
