import pytest

from src.config import settings
from src.database import async_session_maker
from src.models.operations import OperationsOrm
from src.services.provider import restart_pending_operations_helper
from src.statuses import OperationStatus
from src.utils.db_manager import DBManager


@pytest.mark.anyio
async def test_lifespan_restarts_pending_operations(mocker):
    stuck_op_id = "stuck-operation"

    async with DBManager(async_session_maker) as db:

        stuck_op = OperationsOrm(
            operation_id=stuck_op_id,
            amount="5000.00",
            currency="RUB",
            description="Stuck before reboot",
            status=OperationStatus.PROCESSING,
            provider_payment_id=None
        )
        db.session.add(stuck_op)
        await db.session.commit()

    mock_task = mocker.patch("src.services.provider.start_send_to_provider_task")
    await restart_pending_operations_helper()

    mock_task.assert_called_once_with(
        operation_id=stuck_op_id,
        amount="5000.00",
        currency="RUB",
        provider_url=settings.PROVIDER_URL
    )
