import contextvars
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
from backend.core.config import settings

# Context variable to store tenant_id for the current request
tenant_context = contextvars.ContextVar("tenant_id", default="public")

engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    echo=False,
    future=True,
    pool_size=20,
    max_overflow=10
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        tenant_id = tenant_context.get()
        # Set search_path for schema-per-tenant
        if tenant_id and tenant_id != "public":
            # Ensure tenant_id is safe (e.g. UUID format) to prevent SQL injection
            # In a real app, validate the format here.
            await session.execute(text(f'SET search_path TO "{tenant_id}", public'))
        else:
            await session.execute(text('SET search_path TO public'))
        yield session

