from decimal import Decimal

from app.ai.providers.fixture import StaticStructuredGenerator
from app.core.settings import REPOSITORY_ROOT, Settings
from app.main import create_app
from tests.factories import valid_requirements_json

settings = Settings(
    database_url=(
        "sqlite+aiosqlite:///"
        + (REPOSITORY_ROOT / ".local" / "arriendate-e2e.db").as_posix()
    ),
    ai_input_cost_per_million=Decimal("1.00"),
    ai_output_cost_per_million=Decimal("6.00"),
)

app = create_app(
    settings,
    structured_generator=StaticStructuredGenerator(valid_requirements_json()),
)
