from sqlalchemy.ext.asyncio import AsyncSession

from src.models.operations import OperationsOrm
from src.schemas.operations import OperationCreateRequest


class OperationsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_operation(self, data: OperationCreateRequest):
        new_operation = OperationsOrm(
            operation_id=data.operationId,
            amount=data.amount,
            currency=data.currency,
            description=data.description,
            status="CREATED",
        )
        self.session.add(new_operation)
        return new_operation
