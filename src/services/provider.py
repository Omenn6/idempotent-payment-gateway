import asyncio
import logging

import httpx

from src.config import settings
from src.database import async_session_maker
from src.statuses import OperationStatus
from src.utils.db_manager import DBManager

logger = logging.getLogger(__name__)


async def send_to_provider_task(
        operation_id: str,
        amount: str,
        currency: str,
        provider_url: str,
):
    headers = {
        "Content-Type": "application/json",
        "Idempotency-Key": operation_id,
        "X-Correlation-Id": operation_id,
    }
    payload = {
        "operationId": operation_id,
        "amount": amount,
        "currency": currency,
    }

    provider_payment_id = None

    async with httpx.AsyncClient() as client:
        for attempt in range(3):
            try:
                response = await client.post(
                    url=f"{provider_url}/payments",
                    json=payload,
                    headers=headers,
                    timeout=10.0,
                )

                if response.status_code == 202:
                    data = response.json()
                    provider_payment_id = data.get("providerPaymentId")
                    break

                if response.status_code == 503:
                    await asyncio.sleep(1)
                    continue

                break

            except httpx.HTTPError:
                await asyncio.sleep(1)
                continue

        if provider_payment_id is not None:
            async with DBManager(session_factory=async_session_maker) as db:
                operation = await db.operations.get_operation_by_id_for_update(operation_id)

                if operation and operation.status not in [OperationStatus.COMPLETED, OperationStatus.REJECTED]:
                    operation.provider_payment_id = provider_payment_id
                    await db.commit()


async def restart_pending_operations_helper():
    try:
        async with DBManager(session_factory=async_session_maker) as db:
            pending_ops = await db.operations.get_pending_operations()

            if not pending_ops:
                return

            for op in pending_ops:
                asyncio.create_task(
                    send_to_provider_task(
                        operation_id=str(op.operation_id),
                        amount=str(op.amount),
                        currency=str(op.currency),
                        provider_url=settings.PROVIDER_URL,
                    )
                )
    except Exception:
        logger.exception("Ошибка при автоматическом восстановлении операций")
