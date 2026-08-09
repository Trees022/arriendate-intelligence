from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.properties import DEMO_PROPERTIES
from app.db.models import Property


async def seed_demo_properties(session: AsyncSession) -> int:
    """Insert deterministic synthetic inventory into an empty property table."""
    count = await session.scalar(select(func.count()).select_from(Property))
    if count:
        return 0

    session.add_all(Property(**seed.to_record()) for seed in DEMO_PROPERTIES)
    await session.commit()
    return len(DEMO_PROPERTIES)
