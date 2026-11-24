"""Add suppliers and tour expenses.

Revision ID: 0006_suppliers_expenses
Revises: 0005_guides_assignments
Create Date: 2026-11-23

"""

from alembic import op
import sqlalchemy as sa


revision = "0006_suppliers_expenses"
down_revision = "0005_guides_assignments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "suppliers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("service_category", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "length(trim(name)) > 0",
            name=op.f("ck_suppliers_name"),
        ),
        sa.CheckConstraint(
            "length(trim(service_category)) > 0",
            name=op.f("ck_suppliers_service_category"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_suppliers")),
    )

    op.create_table(
        "tour_expenses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("departure_id", sa.Uuid(), nullable=False),
        sa.Column("supplier_id", sa.Uuid(), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "amount > 0",
            name=op.f("ck_tour_expenses_amount"),
        ),
        sa.CheckConstraint(
            "length(trim(category)) > 0",
            name=op.f("ck_tour_expenses_category"),
        ),
        sa.CheckConstraint(
            "length(trim(status)) > 0",
            name=op.f("ck_tour_expenses_status"),
        ),
        sa.ForeignKeyConstraint(
            ["departure_id"],
            ["tour_departures.id"],
            name=op.f("fk_tour_expenses_departure_id_tour_departures"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["supplier_id"],
            ["suppliers.id"],
            name=op.f("fk_tour_expenses_supplier_id_suppliers"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tour_expenses")),
    )
    op.create_index(
        op.f("ix_tour_expenses_departure_id"),
        "tour_expenses",
        ["departure_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tour_expenses_supplier_id"),
        "tour_expenses",
        ["supplier_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_tour_expenses_supplier_id"),
        table_name="tour_expenses",
    )
    op.drop_index(
        op.f("ix_tour_expenses_departure_id"),
        table_name="tour_expenses",
    )
    op.drop_table("tour_expenses")
    op.drop_table("suppliers")
