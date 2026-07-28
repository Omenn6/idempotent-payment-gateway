from fastapi import APIRouter, status

from src.api.dependencies import DBDep
from src.exceptions import (
    OperationAlreadyExistsError,
    OperationAlreadyExistsHTTPException,
)
from src.schemas.operations import OperationCreateRequest
from src.services.operations import OperationService

router = APIRouter()


@router.post("/operations", status_code=status.HTTP_201_CREATED)
async def create_operation(
    operation_data: OperationCreateRequest,
    db: DBDep,
):
    try:
        return await OperationService(db).create_operation(operation_data)
    except OperationAlreadyExistsError:
        raise OperationAlreadyExistsHTTPException
