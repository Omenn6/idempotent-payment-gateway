from sqlalchemy.exc import IntegrityError

from src.exceptions import OperationAlreadyExistsError
from src.schemas.operations import OperationCreateRequest
from src.utils.db_manager import DBManager


class OperationService:
    def __init__(self, db: DBManager | None = None) -> None:
        self.db = db

    async def create_operation(self, operation_data: OperationCreateRequest):
        operation = await self.db.operations.create_operation(operation_data)

        try:
            await self.db.commit()
            return operation

        except IntegrityError:
            raise OperationAlreadyExistsError()
