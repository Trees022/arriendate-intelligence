import os
from decimal import Decimal

from app.ai.contracts import StructuredGenerationRequest, StructuredGenerationResult
from app.ai.providers.fixture import StaticStructuredGenerator
from app.core.settings import REPOSITORY_ROOT, Settings
from app.embeddings.providers.deterministic import DeterministicEmbeddingProvider
from app.main import create_app
from tests.factories import valid_requirements_json


class ScenarioStructuredGenerator:
    provider_name = "fixture"
    model = "fixture-structured-v1"

    async def generate_structured(
        self, request: StructuredGenerationRequest
    ) -> StructuredGenerationResult:
        source = request.messages[-1].content

        if "preferencias semánticas" in source:
            output = valid_requirements_json(
                operation_type="unknown",
                property_types=[],
                locations=[],
                max_budget=None,
                currency=None,
                min_bedrooms=None,
                min_bathrooms=None,
                parking_required=None,
                pets_required=None,
                soft_preferences=["tranquilo", "luminoso", "cerca del mar"],
                missing_information=[
                    "operation_type",
                    "property_type",
                    "location",
                    "budget",
                ],
            )
        elif "presupuesto imposible" in source:
            output = valid_requirements_json(
                max_budget=100_000,
                min_bedrooms=None,
                min_bathrooms=None,
                parking_required=None,
                pets_required=None,
                soft_preferences=["luminoso"],
            )
        else:
            output = valid_requirements_json()

        return await StaticStructuredGenerator(output).generate_structured(request)


e2e_database_url = os.getenv("ARRIENDATE_E2E_DATABASE_URL")

settings = Settings(
    database_url=e2e_database_url
    or (
        "sqlite+aiosqlite:///"
        + (REPOSITORY_ROOT / ".local" / "arriendate-e2e.db").as_posix()
    ),
    seed_demo_data=e2e_database_url is None,
    ai_input_cost_per_million=Decimal("1.00"),
    ai_output_cost_per_million=Decimal("6.00"),
)

app = create_app(
    settings,
    structured_generator=ScenarioStructuredGenerator(),
    embedding_provider=DeterministicEmbeddingProvider(),
)