"""Add guides and tour assignments.

Revision ID: 0005_guides_assignments
Revises: 0004_itineraries
Create Date: 2026-11-23

"""

from alembic import op
import sqlalchemy as sa


revision = "0005_guides_assignments"
down_revision = "0004_itineraries"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "guides",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "length(trim(full_name)) > 0",
            name=op.f("ck_guides_full_name"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_guides_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_guides")),
    )
    op.create_index(op.f("ix_guides_user_id"), "guides", ["user_id"], unique=False)

    op.create_table(
        "tour_assignments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("departure_id", sa.Uuid(), nullable=False),
        sa.Column("guide_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "length(trim(role)) > 0",
            name=op.f("ck_tour_assignments_role"),
        ),
        sa.CheckConstraint(
            "length(trim(status)) > 0",
            name=op.f("ck_tour_assignments_status"),
        ),
        sa.ForeignKeyConstraint(
            ["departure_id"],
            ["tour_departures.id"],
            name=op.f("fk_tour_assignments_departure_id_tour_departures"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["guide_id"],
            ["guides.id"],
            name=op.f("fk_tour_assignments_guide_id_guides"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tour_assignments")),
    )
    op.create_index(
        op.f("ix_tour_assignments_departure_id"),
        "tour_assignments",
        ["departure_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tour_assignments_guide_id"),
        "tour_assignments",
        ["guide_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_tour_assignments_guide_id"),
        table_name="tour_assignments",
    )
    op.drop_index(
        op.f("ix_tour_assignments_departure_id"),
        table_name="tour_assignments",
    )
    op.drop_table("tour_assignments")
    op.drop_index(op.f("ix_guides_user_id"), table_name="guides")
    op.drop_table("guides")
