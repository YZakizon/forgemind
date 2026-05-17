from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from app.config import get_settings


@lru_cache
def get_engine() -> AsyncEngine:
    settings = get_settings()
    return create_async_engine(
        settings.database_url,
        pool_pre_ping=True,
        connect_args={"timeout": 1.0, "command_timeout": 3.0},
    )


@lru_cache
def get_sessionmaker() -> async_sessionmaker:
    return async_sessionmaker(get_engine(), expire_on_commit=False)
