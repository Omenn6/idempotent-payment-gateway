import pytest
from fastapi import status
from httpx import AsyncClient


@pytest.mark.anyio
async def test_get_operation_success(client: AsyncClient, create_operation):
    operation_id = create_operation

    response = await client.get(f"/operations/{operation_id}")

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["operationId"] == operation_id
    assert data["amount"] == "1000.00"
    assert data["currency"] == "RUB"
    assert data["description"] == "test description"
    assert data["status"] == "CREATED"
    assert "providerPaymentId" in data
    assert data["providerPaymentId"] is None


@pytest.mark.anyio
async def test_get_operation_not_found(client: AsyncClient):
    non_existent_id = "unknown-operation"
    response = await client.get(f"/operations/{non_existent_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
