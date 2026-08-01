from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.operations import OperationsOrm
from src.schemas.operations import OperationCreateRequest
from src.statuses import OperationStatus


class OperationsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_operation(self, data: OperationCreateRequest):
        new_operation = OperationsOrm(
            operation_id=data.operation_id,
            amount=data.amount,
            currency=data.currency,
            description=data.description,
            status=OperationStatus.CREATED,
        )
        self.session.add(new_operation)
        return new_operation

    async def get_operation_by_id_for_update(self, operation_id: str):
        query = select(OperationsOrm).filter_by(operation_id=operation_id).with_for_update()
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_pending_operations(self):
        query = select(OperationsOrm).filter_by(status=OperationStatus.PROCESSING)
        result = await self.session.execute(query)
        return result.scalars().all()
