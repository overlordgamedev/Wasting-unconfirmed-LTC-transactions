from sqlalchemy import Column, String
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

# База данных
engine = create_async_engine("postgresql+asyncpg://postgres:postgres@localhost:5432/postgres", echo=False, pool_size=100, max_overflow=500)
session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

class PrivateKeyAddress(Base):
    __tablename__ = 'ltc_private_key_address'
    private_key = Column(String, primary_key=True)
    address = Column(String, nullable=False)


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
