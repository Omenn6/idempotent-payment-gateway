import pytest
from fastapi import status
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text

from src.api.dependencies import get_db
from src.database import Base, async_session_maker_null_pool, engine_null_pool
from src.main import app
from src.utils.db_manager import DBManager


async def get_db_null_pool():
    async with DBManager(session_factory=async_session_maker_null_pool) as db:
        yield db


app.dependency_overrides[get_db] = get_db_null_pool


@pytest.fixture(scope="session", autouse=True)
async def setup_database():
    async with engine_null_pool.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


@pytest.fixture(autouse=True)
async def clean_database():
    async with DBManager(session_factory=async_session_maker_null_pool) as db:
        await db.session.execute(text("TRUNCATE TABLE operations, operation_events RESTART IDENTITY CASCADE;"))
        await db.commit()


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture(scope="function")
async def create_operation(client):
    payload ={
        "operationId": "test-operation",
        "amount": "1000.00",
        "currency": "RUB",
        "description": "test description",
    }
    response = await client.post("/operations", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    return payload["operationId"]
