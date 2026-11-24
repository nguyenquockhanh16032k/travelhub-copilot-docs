"""Add pending booking expiration.

Revision ID: 0009_pending_booking_expiration
Revises: 0008_audit_logs
Create Date: 2026-11-24

"""

from alembic import op
import sqlalchemy as sa


revision = "0009_pending_booking_expiration"
down_revision = "0008_audit_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "bookings",
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_bookings_expires_at",
        "bookings",
        ["expires_at"],
        unique=False,
    )
    op.execute(
        "ALTER TYPE booking_status ADD VALUE IF NOT EXISTS 'expired'"
    )
    op.execute(
        "ALTER TYPE booking_status ADD VALUE IF NOT EXISTS 'rejected'"
    )


def downgrade() -> None:
    op.drop_index("ix_bookings_expires_at", table_name="bookings")
    op.drop_column("bookings", "expires_at")
