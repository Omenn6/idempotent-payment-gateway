import logging
from typing import Sequence

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from src.exceptions import (
    OperationAlreadyExistsError,
    OperationNotFoundError,
    ProviderPaymentIdMismatchError,
    DatabaseUnavailableError,
)
from src.models.operations import OperationsOrm, OperationEventsOrm
from src.schemas.operations import OperationCreateRequest, ReceiptCallbackRequest
from src.utils.db_manager import DBManager
from src.utils.structured_logging import log_event
from src.statuses import OperationStatus


class OperationService:
    def __init__(self, db: DBManager | None = None) -> None:
        self.db = db

    async def check_health(self) -> None:
        try:
            await self.db.session.execute(text("SELECT 1"))
        except SQLAlchemyError:
            raise DatabaseUnavailableError

    async def create_operation(self, operation_data: OperationCreateRequest) -> OperationsOrm:
        operation = await self.db.operations.create_operation(operation_data)

        try:
            await self.db.operations.add_event(
                operation_id=operation.operation_id,
                event_type=OperationStatus.CREATED.value,
                from_status=None,
                to_status=OperationStatus.CREATED,
                message="Operation created",
            )
            await self.db.commit()
            return operation

        except IntegrityError:
            raise OperationAlreadyExistsError

    async def submit_operation(self, operation_id: str) -> tuple[OperationsOrm, bool]:
        operation = await self.db.operations.get_operation_by_id_for_update(operation_id)

        if operation is None:
            raise OperationNotFoundError

        if operation.status == OperationStatus.CREATED:
            old_status = operation.status
            operation.status = OperationStatus.PROCESSING
            await self.db.operations.add_event(
                operation_id=operation.operation_id,
                event_type=OperationStatus.PROCESSING.value,
                from_status=old_status,
                to_status=OperationStatus.PROCESSING,
                message="Operation submitted for processing",
            )

            await self.db.commit()
            return operation, True

        return operation, False

    async def process_receipt(self, callback_data: ReceiptCallbackRequest) -> None:
        operation = await self.db.operations.get_operation_by_id_for_update(callback_data.operation_id)

        if operation is None:
            raise OperationNotFoundError

        if operation.provider_payment_id is not None:
            if operation.provider_payment_id != callback_data.provider_payment_id:
                raise ProviderPaymentIdMismatchError
        else:
            operation.provider_payment_id = callback_data.provider_payment_id

        if operation.status in [OperationStatus.COMPLETED, OperationStatus.REJECTED]:
            if operation.status.value != callback_data.result:
                log_event(
                    level=logging.WARNING,
                    message="Поздняя квитанция с противоположным результатом проигнорирована",
                    operation_id=operation.operation_id,
                    provider_payment_id=operation.provider_payment_id
                )
            return

        old_status = operation.status
        new_status = (
            OperationStatus.COMPLETED
            if callback_data.result == "COMPLETED"
            else OperationStatus.REJECTED
        )

        operation.status = new_status

        await self.db.operations.add_event(
            operation_id=operation.operation_id,
            event_type=new_status.value,
            from_status=old_status,
            to_status=new_status,
            message=callback_data.message,
        )

        await self.db.commit()

    async def get_operation(self, operation_id: str) -> OperationsOrm:
        operation = await self.db.operations.get_operation_by_id(operation_id)
        if operation is None:
            raise OperationNotFoundError
        return operation

    async def get_operation_events(self, operation_id: str) -> Sequence[OperationEventsOrm]:
        operation = await self.db.operations.get_operation_by_id_for_update(operation_id)

        if operation is None:
            raise OperationNotFoundError

        return await self.db.operations.get_operation_events(operation_id)
