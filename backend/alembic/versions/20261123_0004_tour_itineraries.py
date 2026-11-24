"""Add ordered tour itinerary items.

Revision ID: 0004_itineraries
Revises: 0003_booking
Create Date: 2026-11-23

"""

from alembic import op
import sqlalchemy as sa


revision = "0004_itineraries"
down_revision = "0003_booking"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tour_itineraries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tour_id", sa.Uuid(), nullable=False),
        sa.Column("day_number", sa.Integer(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("activity", sa.String(length=255), nullable=False),
        sa.Column("time", sa.String(length=50), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "day_number > 0",
            name=op.f("ck_tour_itineraries_day_number"),
        ),
        sa.CheckConstraint(
            "sequence > 0",
            name=op.f("ck_tour_itineraries_sequence"),
        ),
        sa.ForeignKeyConstraint(
            ["tour_id"],
            ["tours.id"],
            name=op.f("fk_tour_itineraries_tour_id_tours"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tour_itineraries")),
        sa.UniqueConstraint(
            "tour_id",
            "day_number",
            "sequence",
            name="uq_tour_itineraries_tour_day_sequence",
        ),
    )
    op.create_index(
        op.f("ix_tour_itineraries_tour_id"),
        "tour_itineraries",
        ["tour_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_tour_itineraries_tour_id"),
        table_name="tour_itineraries",
    )
    op.drop_table("tour_itineraries")
