"""Initial migration

Revision ID: 83111393e45a
Revises: 
Create Date: 2026-08-09 21:57:24.563110

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '83111393e45a'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('operation_events',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('operation_id', sa.String(length=100), nullable=False),
    sa.Column('event_id', sa.Integer(), nullable=False),
    sa.Column('type', sa.String(length=50), nullable=False),
    sa.Column('from_status', sa.Enum('CREATED', 'PROCESSING', 'COMPLETED', 'REJECTED', name='operationstatus', native_enum=False, length=30), nullable=True),
    sa.Column('to_status', sa.Enum('CREATED', 'PROCESSING', 'COMPLETED', 'REJECTED', name='operationstatus', native_enum=False, length=30), nullable=False),
    sa.Column('message', sa.String(length=255), nullable=False),
    sa.Column('occurred_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('operation_id', 'event_id', name='uq_operation_event_id')
    )
    op.create_index(op.f('ix_operation_events_operation_id'), 'operation_events', ['operation_id'], unique=False)
    op.create_table('operations',
    sa.Column('operation_id', sa.String(length=100), nullable=False),
    sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('description', sa.String(length=255), nullable=False),
    sa.Column('status', sa.Enum('CREATED', 'PROCESSING', 'COMPLETED', 'REJECTED', name='operationstatus', native_enum=False, length=30), nullable=False),
    sa.Column('provider_payment_id', sa.String(length=255), nullable=True),
    sa.CheckConstraint('amount > 0', name='check_amount_positive'),
    sa.PrimaryKeyConstraint('operation_id')
    )


def downgrade() -> None:
    op.drop_table('operations')
    op.drop_index(op.f('ix_operation_events_operation_id'), table_name='operation_events')
    op.drop_table('operation_events')
