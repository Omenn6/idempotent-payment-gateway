from typing import Sequence

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.operations import OperationsOrm, OperationEventsOrm
from src.schemas.operations import OperationCreateRequest
from src.statuses import OperationStatus


class OperationsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_operation(self, data: OperationCreateRequest) -> OperationsOrm:
        new_operation = OperationsOrm(
            operation_id=data.operation_id,
            amount=data.amount,
            currency=data.currency,
            description=data.description,
            status=OperationStatus.CREATED,
        )
        self.session.add(new_operation)
        return new_operation

    async def get_operation_by_id_for_update(self, operation_id: str) -> OperationsOrm | None:
        query = select(OperationsOrm).filter_by(operation_id=operation_id).with_for_update()
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_pending_operations(self) -> Sequence[OperationsOrm]:
        query = select(OperationsOrm).filter_by(status=OperationStatus.PROCESSING)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def add_event(
            self,
            operation_id: str,
            event_type: str,
            from_status: OperationStatus | None,
            to_status: OperationStatus,
            message: str
    ) -> None:
        query_next_id = (
            select(func.coalesce(func.max(OperationEventsOrm.event_id), 0) + 1)
            .filter_by(operation_id=operation_id)
        )

        result = await self.session.execute(query_next_id)
        next_event_id = result.scalar()

        new_event = OperationEventsOrm(
            operation_id=operation_id,
            event_id=next_event_id,
            type=event_type,
            from_status=from_status,
            to_status=to_status,
            message=message,
            occurred_at=func.now(),
        )

        self.session.add(new_event)

    async def get_operation_by_id(self, operation_id: str) -> OperationsOrm | None:
        query = select(OperationsOrm).filter_by(operation_id=operation_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_operation_events(self, operation_id: str) -> Sequence[OperationEventsOrm]:
        query = (
            select(OperationEventsOrm)
            .filter_by(operation_id=operation_id)
            .order_by(OperationEventsOrm.event_id.asc())
        )
        result = await self.session.execute(query)
        return result.scalars().all()
