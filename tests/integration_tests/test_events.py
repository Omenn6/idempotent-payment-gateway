import pytest
from fastapi import status
from httpx import AsyncClient

from src.statuses import OperationStatus


@pytest.mark.anyio
async def test_get_operation_events_full_lifecycle(client: AsyncClient):
    operation_id = "lifecycle-operation-1"
    provider_payment_id = "event-test-uuid-1"

    create_response = await client.post(
        "/operations",
        json={
            "operationId": operation_id,
            "amount": "100.00",
            "currency": "RUB",
            "description": "Тест истории",
        },
    )
    assert create_response.status_code == status.HTTP_201_CREATED

    callback_message = "Платёж успешно проведён банком"
    callback_response = await client.post(
        "/receipts",
        json={
            "providerPaymentId": provider_payment_id,
            "operationId": operation_id,
            "result": OperationStatus.COMPLETED.value,
            "message": callback_message,
            "occurredAt": "2026-07-15T12:00:00Z",
        },
    )
    assert callback_response.status_code == status.HTTP_204_NO_CONTENT

    response = await client.get(f"/operations/{operation_id}/events")
    assert response.status_code == status.HTTP_200_OK

    events = response.json()
    assert len(events) >= 2

    assert events[0]["type"] == OperationStatus.CREATED.value
    assert events[-1]["type"] == OperationStatus.COMPLETED.value
    assert events[-1]["message"] == callback_message


@pytest.mark.anyio
async def test_get_operation_events_not_found(client: AsyncClient):
    invalid_id = "absent-operation-1"
    response = await client.get(f"/operations/{invalid_id}/events")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Операция с таким operationId не найдена"


@pytest.mark.anyio
async def test_get_operation_events_sorting(client: AsyncClient):
    operation_id = "sorting-operation-1"
    provider_payment_id = "event-test-uuid-2"

    await client.post(
        "/operations",
        json={
            "operationId": operation_id,
            "amount": "50.00",
            "currency": "RUB",
            "description": "Проверка сортировки",
        },
    )
    await client.post(
        "/receipts",
        json={
            "providerPaymentId": provider_payment_id,
            "operationId": operation_id,
            "result": OperationStatus.COMPLETED.value,
            "message": "Success",
            "occurredAt": "2026-07-15T12:00:00Z",
        },
    )
    response = await client.get(f"/operations/{operation_id}/events")
    assert response.status_code == status.HTTP_200_OK

    events = response.json()
    assert len(events) >= 2

    id_1 = events[0].get("event_id") or events[0].get("eventId")
    id_2 = events[1].get("event_id") or events[1].get("eventId")
    assert id_1 < id_2


@pytest.mark.anyio
async def test_get_operation_events_idempotency_receipts(client: AsyncClient):
    operation_id = "idempotent-operation-1"
    provider_payment_id = "event-test-uuid-3"

    await client.post(
        "/operations",
        json={
            "operationId": operation_id,
            "amount": "250.00",
            "currency": "RUB",
            "description": "Дубли",
        },
    )

    receipt_payload = {
        "providerPaymentId": provider_payment_id,
        "operationId": operation_id,
        "result": OperationStatus.COMPLETED.value,
        "message": "Успешный платеж",
        "occurredAt": "2026-07-15T12:00:00Z",
    }
    response_1 = await client.post("/receipts", json=receipt_payload)
    assert response_1.status_code == status.HTTP_204_NO_CONTENT

    response_2 = await client.post("/receipts", json=receipt_payload)
    assert response_2.status_code == status.HTTP_204_NO_CONTENT

    conflict_payload = receipt_payload.copy()
    conflict_payload["result"] = OperationStatus.REJECTED.value
    conflict_payload["message"] = "Отказ банка после успеха"

    response_3 = await client.post("/receipts", json=conflict_payload)
    assert response_3.status_code == status.HTTP_204_NO_CONTENT

    response = await client.get(f"/operations/{operation_id}/events")
    events = response.json()

    last_event_status = (
        events[-1].get("to_status")
        or events[-1].get("toStatus")
        or events[-1].get("type")
    )
    assert last_event_status == OperationStatus.COMPLETED.value
