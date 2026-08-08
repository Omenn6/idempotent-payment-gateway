import asyncio
import json
import logging
import random

import httpx

from src.config import settings
from src.database import async_session_maker
from src.statuses import OperationStatus
from src.utils.db_manager import DBManager
from src.utils.structured_logging import log_event

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
        "X-Correlation-ID": operation_id,
    }
    payload = {
        "operationId": operation_id,
        "amount": amount,
        "currency": currency,
    }
    provider_payment_id = None

    base_delay = 1.0
    max_delay = 10.0
    max_attempts = 5

    log_event(
        logging.INFO,
        "Запуск отправки платежа провайдеру",
        operation_id,
    )

    async with httpx.AsyncClient() as client:
        for attempt in range(1, max_attempts + 1):
            try:
                log_event(
                    logging.INFO,
                    "Отправка HTTP POST запроса к провайдеру",
                    operation_id,
                    attempt=attempt,
                )

                response = await client.post(
                    url=f"{provider_url}/payments",
                    json=payload,
                    headers=headers,
                    timeout=10.0,
                )
                if response.status_code == 202:
                    data = response.json()
                    provider_payment_id = data.get("providerPaymentId")
                    log_event(
                        logging.INFO,
                        "Провайдер успешно принял платёж",
                        operation_id,
                        provider_payment_id=provider_payment_id,
                        attempt=attempt,
                    )
                    break

                if response.status_code == 503:
                    delay = min(
                        max_delay, base_delay * (2 ** (attempt - 1))
                    )
                    jittered_delay = random.uniform(0, delay)
                    log_event(
                        logging.WARNING,
                        f"Провайдер вернул 503. Повтор через {jittered_delay:.2f} сек.",
                        operation_id,
                        attempt=attempt,
                        extra_fields={"status_code": 503},
                    )
                    await asyncio.sleep(jittered_delay)
                    continue

                log_event(
                    logging.ERROR,
                    f"Провайдер вернул критическую ошибку {response.status_code}, прерываем попытки",
                    operation_id,
                    attempt=attempt,
                    extra_fields={"status_code": response.status_code},
                )
                break

            except httpx.HTTPError as exc:
                delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
                jittered_delay = random.uniform(0, delay)

                log_event(
                    logging.WARNING,
                    f"Сетевой сбой при вызове провайдера. Повтор через {jittered_delay:.2f} сек.",
                    operation_id,
                    attempt=attempt,
                    extra_fields={"error_type": type(exc).__name__},
                )
                await asyncio.sleep(jittered_delay)
                continue

    if provider_payment_id is not None:
        async with DBManager(session_factory=async_session_maker) as db:
            operation = (
                await db.operations.get_operation_by_id_for_update(
                    operation_id
                )
            )

            if operation and operation.status not in [
                OperationStatus.COMPLETED,
                OperationStatus.REJECTED,
            ]:
                operation.provider_payment_id = provider_payment_id
                await db.commit()
                log_event(
                    logging.INFO,
                    "Идентификатор платежа успешно сохранён в БД",
                    operation_id,
                    provider_payment_id=provider_payment_id,
                )
    else:
        log_event(
            logging.ERROR,
            "Не удалось получить providerPaymentId после всех попыток фоновой обработки",
            operation_id,
        )


async def restart_pending_operations_helper():
    try:
        async with DBManager(session_factory=async_session_maker) as db:
            pending_ops = await db.operations.get_pending_operations()

            if not pending_ops:
                return
            for op in pending_ops:
                log_event(
                    logging.INFO,
                    "Автоматическое возобновление незавершенной операции из статуса PROCESSING",
                    operation_id=str(op.operation_id),
                )
                start_send_to_provider_task(
                    operation_id=str(op.operation_id),
                    amount=str(op.amount),
                    currency=str(op.currency),
                    provider_url=settings.PROVIDER_URL,
                )
    except Exception as exc:
        logger.exception(
            json.dumps(
                {
                    "event": "Критическая ошибка при автоматическом восстановлении операций",
                    "error": str(exc),
                }
            )
        )


active_tasks = set()


def start_send_to_provider_task(operation_id: str, amount: str, currency: str, provider_url: str):
    task = asyncio.create_task(
        send_to_provider_task(
            operation_id=operation_id,
            amount=amount,
            currency=currency,
            provider_url=provider_url
        )
    )
    active_tasks.add(task)
    task.add_done_callback(active_tasks.discard)
    return task


async def shutdown_background_tasks(timeout: float = 10.0):
    if not active_tasks:
        log_event(logging.INFO, "Нет активных фоновых задач для завершения", operation_id=None)
        return

    log_event(
        logging.INFO,
        f"Обнаружено активных фоновых задач: {len(active_tasks)}. Ожидаем их завершения...",
        operation_id=None,
        extra_fields={"timeout": timeout}
    )

    try:
        await asyncio.wait_for(
            asyncio.gather(*active_tasks, return_exceptions=True),
            timeout=timeout
        )
        log_event(logging.INFO, "Все фоновые задачи успешно завершены (Graceful Shutdown)", operation_id=None)
    except asyncio.TimeoutError:
        log_event(
            logging.WARNING,
            "Время ожидания фоновых задач истекло. Некоторые операции будут прерваны и восстановлены при следующем старте.",
            operation_id=None
        )
