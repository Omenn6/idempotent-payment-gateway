import asyncio

from fastapi import status
import pytest

from src.config import settings
from src.database import async_session_maker
from src.services.provider import send_to_provider_task
from src.statuses import OperationStatus
from src.utils.db_manager import DBManager


@pytest.mark.anyio
async def test_submit_operation_first_time_success(client, create_operation, mocker):
    mock_task = mocker.patch("src.api.operations.send_to_provider_task")
    op_id = create_operation
    response = await client.post(f"/operations/{op_id}/submit")

    assert response.status_code == status.HTTP_202_ACCEPTED
    data = response.json()
    assert data["status"] == OperationStatus.PROCESSING
    mock_task.assert_called_once_with(
        operation_id=op_id,
        amount="1000.00",
        currency="RUB",
        provider_url=mocker.ANY,
    )


@pytest.mark.anyio
async def test_submit_operation_repeated_returns_200(client, create_operation, mocker):
    mock_task = mocker.patch("src.api.operations.send_to_provider_task")
    op_id = create_operation

    first_resp = await client.post(f"/operations/{op_id}/submit")
    assert first_resp.status_code == status.HTTP_202_ACCEPTED
    assert mock_task.call_count == 1

    second_resp = await client.post(f"/operations/{op_id}/submit")
    assert second_resp.status_code == status.HTTP_200_OK

    data = second_resp.json()
    assert data["status"] == OperationStatus.PROCESSING
    assert mock_task.call_count == 1


@pytest.mark.anyio
async def test_submit_operation_not_found(client):
    response = await client.post(f"/operations/non-existent-id/submit")
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.anyio
async def test_submit_concurrent_race_condition(client, create_operation, mocker):
    mock_task = mocker.patch("src.api.operations.send_to_provider_task")
    op_id = create_operation

    tasks = [client.post(f"/operations/{op_id}/submit") for _ in range(5)]
    responses = await asyncio.gather(*tasks)

    status_codes = [r.status_code for r in responses]
    assert status_codes.count(status.HTTP_202_ACCEPTED) == 1
    assert status_codes.count(status.HTTP_200_OK) == 4


@pytest.mark.anyio
async def test_send_to_provider_task_retry_on_503(httpx_mock, mocker, create_operation):
    op_id = create_operation

    httpx_mock.add_response(method="POST", status_code=503)
    httpx_mock.add_response(method="POST", status_code=503)
    httpx_mock.add_response(
        method="POST",
        status_code=202,
        json={"providerPaymentId": "uuid-success-789", "status": "ACCEPTED"}
    )
    mock_sleep = mocker.patch("asyncio.sleep", return_value=None)

    await send_to_provider_task(
        operation_id=op_id,
        amount="1000.00",
        currency="RUB",
        provider_url=settings.PROVIDER_URL
    )

    assert len(httpx_mock.get_requests()) == 3
    assert mock_sleep.call_count == 2

    async with DBManager(async_session_maker) as db:
        operation = await db.operations.get_operation_by_id_for_update(op_id)
        assert operation.provider_payment_id == "uuid-success-789"


@pytest.mark.anyio
async def test_send_to_provider_task_exhausts_retries_on_503(httpx_mock, mocker, create_operation):
    op_id = create_operation

    for _ in range(5):
        httpx_mock.add_response(method="POST", status_code=503)

    mock_sleep = mocker.patch("asyncio.sleep", return_value=None)

    try:
        await send_to_provider_task(
            operation_id=op_id,
            amount="1000.00",
            currency="RUB",
            provider_url=settings.PROVIDER_URL
        )
    except Exception:
        pass

    assert len(httpx_mock.get_requests()) == 5
    assert mock_sleep.call_count == 5
