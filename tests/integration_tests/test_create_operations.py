import pytest
from fastapi import status


@pytest.mark.anyio
async def test_create_operation_success(client):
    payload = {
        "operationId": "operation-1",
        "amount": "1000.00",
        "currency": "RUB",
        "description": "test description",
    }

    response = await client.post("/operations", json=payload)

    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()
    assert data["operationId"] == "operation-1"
    assert data["amount"] == "1000.00"
    assert data["currency"] == "RUB"
    assert data["description"] == "test description"
    assert data["status"] == "CREATED"
    assert data["providerPaymentId"] is None


@pytest.mark.anyio
async def test_create_operation_duplicate_conflict(client):
    payload = {
        "operationId": "operation-2",
        "amount": "1000.00",
        "currency": "RUB",
        "description": "test duplicate",
    }

    first_response = await client.post("/operations", json=payload)
    assert first_response.status_code == status.HTTP_201_CREATED

    second_response = await client.post("/operations", json=payload)
    assert second_response.status_code == status.HTTP_409_CONFLICT
