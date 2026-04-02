"""Script to create all database tables directly (for development)."""
import asyncio
from app.database import engine
from app.models.base import Base
# Import all models so they register with Base
from app.models import user, aac_profile, board, board_cell, symbol, usage_log, care_relationship, literacy_milestone

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print("All tables created successfully!")

if __name__ == "__main__":
    asyncio.run(create_tables())
