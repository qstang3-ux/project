from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


@lru_cache
def get_app_engine() -> Engine:
    settings = get_settings()
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        future=True,
        connect_args={"connect_timeout": settings.database_connect_timeout_seconds},
    )


@lru_cache
def get_query_engine() -> Engine:
    settings = get_settings()
    return create_engine(
        settings.query_database_url,
        pool_pre_ping=True,
        future=True,
        connect_args={"connect_timeout": settings.database_connect_timeout_seconds},
    )


def get_session() -> Generator[Session, None, None]:
    factory = sessionmaker(bind=get_app_engine(), expire_on_commit=False)
    with factory() as session:
        yield session


def new_session() -> Session:
    return sessionmaker(bind=get_app_engine(), expire_on_commit=False)()


def dispose_engines() -> None:
    if get_app_engine.cache_info().currsize:
        get_app_engine().dispose()
    if get_query_engine.cache_info().currsize:
        get_query_engine().dispose()
