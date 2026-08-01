from fastapi import APIRouter, BackgroundTasks, Response, status

from src.config import settings
from src.api.dependencies import DBDep
from src.exceptions import (
    OperationAlreadyExistsError,
    OperationAlreadyExistsHTTPException,
    OperationNotFoundError,
    OperationNotFoundHTTPException,
)
from src.schemas.operations import OperationCreateRequest, OperationResponse
from src.services.operations import OperationService
from src.services.provider import send_to_provider_task


router = APIRouter()


@router.post("/operations", status_code=status.HTTP_201_CREATED, response_model=OperationResponse)
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
