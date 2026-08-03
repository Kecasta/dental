from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from config.settings import settings
from src.database.models import Base

# Crear motor asíncrono
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True
)

# Creador de sesiones asíncronas
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def init_db():
    """Inicializa la estructura de tablas en la base de datos."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db_session() -> AsyncSession:
    """Retorna un generador de sesión asíncrona."""
    async with async_session_factory() as session:
        yield session
