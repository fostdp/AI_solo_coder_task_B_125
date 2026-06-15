from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import create_engine
from config import settings

Base = declarative_base()

async_engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=10
)

async_session = sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

sync_engine = create_engine(
    settings.timescaledb_url,
    echo=settings.debug,
    pool_pre_ping=True
)

sync_session = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)


async def get_db():
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_sync_db():
    db = sync_session()
    try:
        yield db
    finally:
        db.close()
