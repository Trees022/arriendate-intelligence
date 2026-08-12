from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.contracts import StructuredGenerator
from app.core.settings import Settings
from app.db.session import Database
from app.embeddings.contracts import EmbeddingProvider


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    database: Database = request.app.state.database
    async with database.session() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_structured_generator(request: Request) -> StructuredGenerator:
    generator: StructuredGenerator = request.app.state.structured_generator
    return generator


def get_app_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def get_embedding_provider(request: Request) -> EmbeddingProvider:
    provider: EmbeddingProvider = request.app.state.embedding_provider
    return provider


GeneratorDep = Annotated[StructuredGenerator, Depends(get_structured_generator)]
SettingsDep = Annotated[Settings, Depends(get_app_settings)]
EmbeddingProviderDep = Annotated[EmbeddingProvider, Depends(get_embedding_provider)]
