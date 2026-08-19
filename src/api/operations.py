import logging

from typing import List

from fastapi import APIRouter, Response, status, Path

from src.config import settings
from src.api.dependencies import DBDep
from src.exceptions import (
    OperationAlreadyExistsError,
    OperationAlreadyExistsHTTPException,
    OperationNotFoundError,
    OperationNotFoundHTTPException,
    ProviderPaymentIdMismatchError,
    ProviderPaymentIdMismatchHTTPException,
    DatabaseUnavailableError,
    DatabaseUnavailableHTTPException,
)
from src.schemas.operations import (
    OperationCreateRequest,
    OperationResponse,
    ReceiptCallbackRequest,
    OperationEventResponse
)
from src.services.operations import OperationService
from src.services.provider import start_send_to_provider_task, active_tasks
from src.utils.structured_logging import log_event
from src.utils.metrics import metrics


router = APIRouter()


@router.get(
    "/health",
    response_class=Response,
    status_code=status.HTTP_200_OK,
    summary="Проверить работоспособность сервиса",
)
async def health_check(db: DBDep):
    try:
        await OperationService(db).check_health()
        return Response(status_code=status.HTTP_200_OK)
    except DatabaseUnavailableError:
        raise DatabaseUnavailableHTTPException


@router.post(
    "/operations",
    response_model=OperationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать новую операцию"
)
async def create_operation(
    operation_data: OperationCreateRequest,
    db: DBDep,
):
    try:
        return await OperationService(db).create_operation(operation_data)
    except OperationAlreadyExistsError:
        raise OperationAlreadyExistsHTTPException


@router.post(
    "/operations/{id}/submit",
    response_model=OperationResponse,
    summary="Отправить операцию на обработку",
)
async def submit_operation(
    db: DBDep,
    response: Response,
    operation_id: str = Path(..., alias="id"),
):
    try:
        operation, is_first_submit = await OperationService(db).submit_operation(operation_id)

        if is_first_submit:
            response.status_code = status.HTTP_202_ACCEPTED

            log_event(
                logging.INFO,
                "Команда на первичную отправку платежа принята",
                operation_id=operation_id
            )
            
            start_send_to_provider_task(
                operation_id=str(operation.operation_id),
                amount=str(operation.amount),
                currency=str(operation.currency),
                provider_url=settings.PROVIDER_URL,
            )
        else:
            response.status_code = status.HTTP_200_OK

        return operation

    except OperationNotFoundError:
        raise OperationNotFoundHTTPException


@router.post(
    "/receipts",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Принять callback-квитанцию от провайдера"
)
async def receive_receipt(
    callback_data: ReceiptCallbackRequest,
    db: DBDep,
):
    try:
        await OperationService(db).process_receipt(callback_data)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except OperationNotFoundError:
        raise OperationNotFoundHTTPException

    except ProviderPaymentIdMismatchError:
        raise ProviderPaymentIdMismatchHTTPException


@router.get(
    "/operations/{id}",
    response_model=OperationResponse,
    status_code=status.HTTP_200_OK,
    summary="Получить текущее состояние операции"
)
async def get_operation(
    db: DBDep,
    operation_id: str = Path(..., alias="id"),
):
    try:
        return await OperationService(db).get_operation(operation_id)
    except OperationNotFoundError:
        raise OperationNotFoundHTTPException


@router.get(
    "/operations/{id}/events",
    response_model=List[OperationEventResponse],
    status_code=status.HTTP_200_OK,
    summary="Получить историю изменений статусов операции"
)
async def get_operation_events(
    db: DBDep,
    operation_id: str = Path(..., alias="id"),
):
    try:
        return await OperationService(db).get_operation_events(operation_id)
    except OperationNotFoundError:
        raise OperationNotFoundHTTPException


@router.get("/metrics", summary="Получить метрики сервиса")
async def get_metrics():
    return {
        "retry_count": metrics.retry_count,
        "pending_operations_count": len(active_tasks)
    }
