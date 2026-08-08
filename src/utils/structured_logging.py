import json
import logging

logger = logging.getLogger("payment_system")


def log_event(
    level: int,
    message: str,
    operation_id: str | None = None,
    provider_payment_id: str | None = None,
    attempt: int | None = None,
    extra_fields: dict | None = None,
):
    log_data = {
        "event": message,
        "operationId": operation_id,
        "providerPaymentId": provider_payment_id,
        "attempt": attempt,
    }

    if extra_fields:
        log_data.update(extra_fields)

    cleaned_log_data = {
        key: value
        for key, value in log_data.items()
        if value is not None or key == "operationId"
    }

    logger.log(level, json.dumps(cleaned_log_data, ensure_ascii=False))
