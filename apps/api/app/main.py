import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from app.ai.contracts import StructuredGenerator
from app.ai.factory import build_structured_generator
from app.api.routes import health, leads, properties
from app.core.errors import AppError
from app.core.settings import Settings, get_settings
from app.db.seed import seed_demo_properties
from app.db.session import Database


def create_app(
    settings: Settings | None = None,
    structured_generator: StructuredGenerator | None = None,
) -> FastAPI:
    app_settings = settings or get_settings()
    generator = structured_generator or build_structured_generator(app_settings)
    logging.basicConfig(
        level=app_settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        database = Database(app_settings.database_url)
        app.state.database = database
        await database.initialize_local_schema()
        if app_settings.seed_demo_data:
            async with database.session() as session:
                await seed_demo_properties(session)
        yield
        await database.dispose()

    application = FastAPI(
        title=app_settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )
    application.state.settings = app_settings
    application.state.structured_generator = generator
    application.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Idempotency-Key", "X-Request-ID"],
    )

    @application.middleware("http")
    async def request_id_header(request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid4()))[:128]
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    @application.exception_handler(AppError)
    async def handle_app_error(request: Request, error: AppError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        return JSONResponse(
            status_code=error.status_code,
            content={
                "type": f"https://arriendate.local/errors/{error.code}",
                "title": error.code.replace("_", " ").title(),
                "status": error.status_code,
                "detail": error.detail,
                "request_id": request_id,
            },
        )

    application.include_router(health.router, prefix="/api")
    application.include_router(leads.router, prefix="/api")
    application.include_router(properties.router, prefix="/api")
    return application


app = create_app()
