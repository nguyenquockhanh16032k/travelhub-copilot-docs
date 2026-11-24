"""Add article categories and articles.

Revision ID: 0007_articles_categories
Revises: 0006_suppliers_expenses
Create Date: 2026-11-23

"""

from alembic import op
import sqlalchemy as sa


revision = "0007_articles_categories"
down_revision = "0006_suppliers_expenses"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "length(trim(name)) > 0",
            name=op.f("ck_categories_name"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_categories")),
        sa.UniqueConstraint("slug", name=op.f("uq_categories_slug")),
    )

    op.create_table(
        "articles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=True),
        sa.Column("author_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("cover_image_url", sa.String(length=2048), nullable=True),
        sa.Column(
            "status",
            sa.Enum("draft", "published", "archived", name="article_status"),
            nullable=False,
        ),
        sa.Column("seo_title", sa.String(length=255), nullable=True),
        sa.Column("seo_description", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "length(trim(title)) > 0",
            name=op.f("ck_articles_title"),
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            name=op.f("fk_articles_category_id_categories"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["author_id"],
            ["users.id"],
            name=op.f("fk_articles_author_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_articles")),
        sa.UniqueConstraint("slug", name=op.f("uq_articles_slug")),
    )
    op.create_index(
        op.f("ix_articles_category_id"),
        "articles",
        ["category_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_articles_author_id"),
        "articles",
        ["author_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_articles_author_id"), table_name="articles")
    op.drop_index(op.f("ix_articles_category_id"), table_name="articles")
    op.drop_table("articles")
    op.execute("DROP TYPE IF EXISTS article_status")
    op.drop_table("categories")
