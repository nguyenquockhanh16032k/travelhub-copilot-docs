"""Add payment idempotency and financial exception fields.

Revision ID: 0010_payment_management
Revises: 0009_pending_booking_expiration
Create Date: 2026-11-25

"""

from alembic import op
import sqlalchemy as sa


revision = "0010_payment_management"
down_revision = "0009_pending_booking_expiration"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "payments",
        sa.Column(
            "requires_resolution",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )
    op.add_column(
        "payments",
        sa.Column("resolution_reason", sa.Text(), nullable=True),
    )
    op.add_column(
        "payments",
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.add_column(
        "payments",
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "payments",
        sa.Column("idempotency_fingerprint", sa.String(length=64), nullable=True),
    )
    op.create_unique_constraint(
        "uq_payments_idempotency_key",
        "payments",
        ["idempotency_key"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_payments_idempotency_key",
        "payments",
        type_="unique",
    )
    op.drop_column("payments", "idempotency_fingerprint")
    op.drop_column("payments", "idempotency_key")
    op.drop_column("payments", "notes")
    op.drop_column("payments", "resolution_reason")
    op.drop_column("payments", "requires_resolution")
