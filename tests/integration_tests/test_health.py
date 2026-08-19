import pytest
from _pytest.monkeypatch import MonkeyPatch
from fastapi import status
from httpx import AsyncClient

from src.exceptions import DatabaseUnavailableError
from src.services.operations import OperationService


@pytest.mark.anyio
async def test_health_check_success(client: AsyncClient):
    response = await client.get("/health")

    assert response.status_code == status.HTTP_200_OK
    assert response.content == b""


@pytest.mark.anyio
async def test_health_check_database_down(
    client: AsyncClient, monkeypatch: MonkeyPatch
):
    async def mock_check_health(*args, **kwargs):
        raise DatabaseUnavailableError()

    monkeypatch.setattr(OperationService, "check_health", mock_check_health)

    response = await client.get("/health")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json() == {"detail": "База данных временно недоступна"}
