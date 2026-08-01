from sqlalchemy.exc import IntegrityError

from src.exceptions import (
    OperationAlreadyExistsError,
    OperationNotFoundError,
)
from src.schemas.operations import OperationCreateRequest
from src.utils.db_manager import DBManager
from src.statuses import OperationStatus


class OperationService:
    def __init__(self, db: DBManager | None = None) -> None:
        self.db = db

    async def create_operation(self, operation_data: OperationCreateRequest):
        operation = await self.db.operations.create_operation(operation_data)

        try:
            await self.db.commit()
            return operation

        except IntegrityError:
            raise OperationAlreadyExistsError

    async def submit_operation(self, operation_id: str):
        operation = await self.db.operations.get_operation_by_id_for_update(operation_id)

        if operation is None:
            raise OperationNotFoundError

        if operation.status == OperationStatus.CREATED:
            operation.status = OperationStatus.PROCESSING
            await self.db.commit()
            return operation, True

        return operation, False
