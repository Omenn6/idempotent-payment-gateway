from fastapi import APIRouter, BackgroundTasks, Response, status

from src.config import settings
from src.api.dependencies import DBDep
from src.exceptions import (
    OperationAlreadyExistsError,
    OperationAlreadyExistsHTTPException,
    OperationNotFoundError,
    OperationNotFoundHTTPException,
    ProviderPaymentIdMismatchError,
    ProviderPaymentIdMismatchHTTPException,
)
from src.schemas.operations import OperationCreateRequest, OperationResponse, ReceiptCallbackRequest
from src.services.operations import OperationService
from src.services.provider import send_to_provider_task


router = APIRouter()


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
    background_tasks: BackgroundTasks,
    response: Response,
):
    try:
        operation, is_first_submit = await OperationService(db).submit_operation(operation_id)

        if is_first_submit:
            response.status_code = status.HTTP_202_ACCEPTED
            background_tasks.add_task(
                send_to_provider_task,
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
