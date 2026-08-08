from typing import List

from fastapi import APIRouter, Response, status

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
from src.services.provider import start_send_to_provider_task


router = APIRouter()


@router.get("/health", response_class=Response, status_code=status.HTTP_200_OK)
async def health_check(db: DBDep):
    try:
        await OperationService(db).check_health()
        return Response(status_code=status.HTTP_200_OK)
    except DatabaseUnavailableError:
        raise DatabaseUnavailableHTTPException


@router.post("/operations", response_model=OperationResponse, status_code=status.HTTP_201_CREATED)
async def create_operation(
    operation_data: OperationCreateRequest,
    db: DBDep,
):
    try:
        return await OperationService(db).create_operation(operation_data)
    except OperationAlreadyExistsError:
        raise OperationAlreadyExistsHTTPException


@router.post("/operations/{operation_id}/submit")
async def submit_operation(
    operation_id: str,
    db: DBDep,
    response: Response,
):
    try:
        operation, is_first_submit = await OperationService(db).submit_operation(operation_id)

        if is_first_submit:
            response.status_code = status.HTTP_202_ACCEPTED
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


@router.post("/receipts", status_code=status.HTTP_204_NO_CONTENT)
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


@router.get("/operations/{operation_id}", response_model=OperationResponse, status_code=status.HTTP_200_OK)
async def get_operation(
    operation_id: str,
    db: DBDep,
):
    try:
        return await OperationService(db).get_operation(operation_id)
    except OperationNotFoundError:
        raise OperationNotFoundHTTPException


@router.get("/operations/{operation_id}/events", response_model=List[OperationEventResponse], status_code=status.HTTP_200_OK)
async def get_operation_events(
    operation_id: str,
    db: DBDep,
):
    try:
        return await OperationService(db).get_operation_events(operation_id)
    except OperationNotFoundError:
        raise OperationNotFoundHTTPException
