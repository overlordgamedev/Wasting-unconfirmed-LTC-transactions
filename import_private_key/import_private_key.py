import asyncio
import aiofiles
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, String, select

# Определяем базовый класс для моделей
Base = declarative_base()


# Модель для таблицы private_key_address
class PrivateKeyAddress(Base):
    __tablename__ = 'ltc_private_key_address'

    private_key = Column(String, primary_key=True)
    address = Column(String, nullable=False)


# Асинхронная функция для добавления данных в таблицу
async def add_private_key_and_address(session: AsyncSession, private_key: str, address: str):
    query = select(PrivateKeyAddress).filter_by(private_key=private_key)
    result = await session.execute(query)
    existing_entry = result.scalars().first()

    if existing_entry:
        print(f"Запись с приватным ключом {private_key} уже существует, пропускаем.")
        return

    new_entry = PrivateKeyAddress(private_key=private_key, address=address)
    session.add(new_entry)
    await session.commit()
    print(f"Приватный ключ и адрес добавлены: {private_key} - {address}")


# Асинхронная функция для обработки данных из файла
async def process_file_and_add_to_db(file_path: str, session: AsyncSession):
    async with aiofiles.open(file_path, "r", encoding="utf-8") as file:
        async for line in file:
            line = line.strip()

            # Разделение строки на две части, первая часть это приватный ключ, вторая часть это адрес
            private_key, address = line.split(":", 1)

            await add_private_key_and_address(session, private_key.strip(), address.strip())


# Основная асинхронная функция
async def main():
    engine = create_async_engine(DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        # Создаём таблицу, если она ещё не существует
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session:
        await process_file_and_add_to_db(file_path, session)

if __name__ == "__main__":
    DATABASE_URL = 'postgresql+asyncpg://postgres:postgres@localhost:5432/postgres'
    file_path = "./import_private_key/private_key_address.txt"
    asyncio.run(main())
