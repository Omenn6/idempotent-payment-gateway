from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Enum, Numeric, String, UniqueConstraint, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.statuses import OperationStatus


class OperationsOrm(Base):
    __tablename__ = "operations"

    operation_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3))
    description: Mapped[str] = mapped_column(String(255))
    status: Mapped[OperationStatus] = mapped_column(
        Enum(OperationStatus, native_enum=False, length=30),
        default=OperationStatus.CREATED
    )
    provider_payment_id: Mapped[str | None] = mapped_column(String(255), default=None)

    __table_args__ = (
        CheckConstraint("amount > 0", name="check_amount_positive"),
    )


class OperationEventsOrm(Base):
    __tablename__ = "operation_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    operation_id: Mapped[str] = mapped_column(String(100), index=True)
    event_id: Mapped[int] = mapped_column()
    type: Mapped[str] = mapped_column(String(50))
    from_status: Mapped[OperationStatus | None] = mapped_column(
        Enum(OperationStatus, native_enum=False, length=30),
        default=None
    )
    to_status: Mapped[OperationStatus] = mapped_column(
        Enum(OperationStatus, native_enum=False, length=30)
    )
    message: Mapped[str] = mapped_column(String(255))
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("operation_id", "event_id", name="uq_operation_event_id"),
    )
