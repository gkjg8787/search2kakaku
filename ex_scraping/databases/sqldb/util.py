from sqlmodel import Field, Session, SQLModel, create_engine, select
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
)

sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
async_sqlite_url = f"sqlite+aiosqlite:///{sqlite_file_name}"

connect_args = {"check_same_thread": False}

engine = create_engine(sqlite_url, echo=False, connect_args=connect_args)

async_engine = create_async_engine(
    async_sqlite_url, echo=False, connect_args=connect_args
)
aSessionLocal = async_sessionmaker(autocommit=False, autoflush=True, bind=async_engine)


async def get_async_session():
    async with aSessionLocal() as ses:
        yield ses


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


async def create_async_db_and_tables():
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


def get_engine():
    return engine


def get_async_engine():
    return async_engine
