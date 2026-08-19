import asyncio

import pytest
from fastapi import status
from httpx import AsyncClient

from src.database import async_session_maker_null_pool
from src.utils.db_manager import DBManager


@pytest.mark.anyio
async def test_receipt_success_completed(client: AsyncClient, create_operation: str):
    operation_id = create_operation
    provider_payment_id = "successful-test-uuid"

    payload = {
        "providerPaymentId": provider_payment_id,
        "operationId": operation_id,
        "result": "COMPLETED",
        "message": "Payment completed successfully",
        "occurredAt": "2026-07-15T12:00:00Z",
    }

    response = await client.post("/receipts", json=payload)
    assert response.status_code == status.HTTP_204_NO_CONTENT

    async with DBManager(session_factory=async_session_maker_null_pool) as db:
        op = await db.operations.get_operation_by_id_for_update(operation_id)
        assert op is not None
        assert op.status == "COMPLETED"
        assert op.provider_payment_id == provider_payment_id


@pytest.mark.anyio
async def test_receipt_idempotent_repeat(client: AsyncClient, create_operation: str):
    operation_id = create_operation
    payload = {
        "providerPaymentId": "successful-test-uuid",
        "operationId": operation_id,
        "result": "COMPLETED",
        "message": "Payment completed successfully",
        "occurredAt": "2026-07-15T12:00:00Z",
    }

    response_1 = await client.post("/receipts", json=payload)
    assert response_1.status_code == status.HTTP_204_NO_CONTENT

    response_2 = await client.post("/receipts", json=payload)
    assert response_2.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.anyio
async def test_receipt_late_conflict(client: AsyncClient, create_operation: str):
    operation_id = create_operation
    provider_payment_id = "successful-test-uuid"

    payload_completed = {
        "providerPaymentId": provider_payment_id,
        "operationId": operation_id,
        "result": "COMPLETED",
        "message": "Success",
        "occurredAt": "2026-07-15T12:00:00Z",
    }
    await client.post("/receipts", json=payload_completed)

    payload_rejected = {
        "providerPaymentId": provider_payment_id,
        "operationId": operation_id,
        "result": "REJECTED",
        "message": "Late mistake reject",
        "occurredAt": "2026-07-15T12:05:00Z",
    }
    response = await client.post("/receipts", json=payload_rejected)

    assert response.status_code == status.HTTP_204_NO_CONTENT

    async with DBManager(session_factory=async_session_maker_null_pool) as db:
        op = await db.operations.get_operation_by_id_for_update(operation_id)
        assert op.status == "COMPLETED"


@pytest.mark.anyio
async def test_receipt_mismatched_provider_payment_id(
    client: AsyncClient, create_operation: str
):
    operation_id = create_operation

    payload_correct = {
        "providerPaymentId": "correct-provider-uuid",
        "operationId": operation_id,
        "result": "COMPLETED",
        "message": "First correct bind",
        "occurredAt": "2026-07-15T12:00:00Z",
    }
    await client.post("/receipts", json=payload_correct)

    payload_wrong = {
        "providerPaymentId": "fraudulent-or-wrong-uuid",
        "operationId": operation_id,
        "result": "COMPLETED",
        "message": "Mismatched attempt",
        "occurredAt": "2026-07-15T12:01:00Z",
    }
    response = await client.post("/receipts", json=payload_wrong)

    assert response.status_code == status.HTTP_409_CONFLICT


@pytest.mark.anyio
async def test_receipt_not_found(client: AsyncClient):
    payload = {
        "providerPaymentId": "successful-test-uuid",
        "operationId": "unknown-operation-id-12345",
        "result": "COMPLETED",
        "message": "Ghost receipt",
        "occurredAt": "2026-07-15T12:00:00Z",
    }
    response = await client.post("/receipts", json=payload)
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.anyio
async def test_receipt_race_condition(client: AsyncClient, create_operation: str):
    operation_id = create_operation
    payload = {
        "providerPaymentId": "race-receipt-uuid",
        "operationId": operation_id,
        "result": "COMPLETED",
        "message": "Race request",
        "occurredAt": "2026-07-15T12:00:00Z",
    }

    results = await asyncio.gather(
        client.post("/receipts", json=payload), client.post("/receipts", json=payload)
    )

    for response in results:
        assert response.status_code == status.HTTP_204_NO_CONTENT
