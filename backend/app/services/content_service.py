import math
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.content import Article, Category
from app.models.identity import User
from app.schemas.content import (
    ArticleCreate,
    ArticleUpdate,
    CategoryCreate,
    CategoryUpdate,
)


class ContentError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def list_categories(db: Session) -> list[Category]:
    return list(db.scalars(select(Category).order_by(Category.name, Category.id)))


def create_category(db: Session, payload: CategoryCreate) -> Category:
    if db.scalar(select(Category).where(Category.slug == payload.slug)):
        raise ContentError("CATEGORY_SLUG_EXISTS", "A category with this slug exists")
    category = Category(**payload.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def update_category(
    db: Session,
    category_id: UUID,
    payload: CategoryUpdate,
) -> Category:
    category = db.get(Category, category_id)
    if category is None:
        raise ContentError("CATEGORY_NOT_FOUND", "Category not found")
    values = payload.model_dump(exclude_unset=True)
    if "slug" in values:
        existing = db.scalar(
            select(Category).where(
                Category.slug == values["slug"],
                Category.id != category_id,
            )
        )
        if existing:
            raise ContentError("CATEGORY_SLUG_EXISTS", "A category with this slug exists")
    for field, value in values.items():
        setattr(category, field, value)
    db.commit()
    db.refresh(category)
    return category


def list_articles(
    db: Session,
    page: int,
    size: int,
    search: str | None,
    published_only: bool,
    category_id: UUID | None = None,
) -> tuple[list[Article], int, int]:
    query = select(Article).options(selectinload(Article.category))
    count_query = select(func.count(Article.id))
    if published_only:
        query = query.where(Article.status == "published")
        count_query = count_query.where(Article.status == "published")
    if category_id is not None:
        query = query.where(Article.category_id == category_id)
        count_query = count_query.where(Article.category_id == category_id)
    if search:
        pattern = f"%{search.strip()}%"
        filter_clause = or_(Article.title.ilike(pattern), Article.slug.ilike(pattern))
        query = query.where(filter_clause)
        count_query = count_query.where(filter_clause)
    query = query.order_by(
        Article.published_at.desc().nullslast(),
        Article.created_at.desc(),
    )
    items = list(db.scalars(query.offset((page - 1) * size).limit(size)))
    total = int(db.scalar(count_query) or 0)
    return items, total, math.ceil(total / size) if total else 0


def get_published_article(db: Session, slug: str) -> Article:
    article = db.scalar(
        select(Article)
        .where(Article.slug == slug, Article.status == "published")
        .options(selectinload(Article.category))
    )
    if article is None:
        raise ContentError("ARTICLE_NOT_FOUND", "Published article not found")
    return article


def get_manageable_article(db: Session, article_id: UUID) -> Article:
    article = db.scalar(
        select(Article)
        .where(Article.id == article_id)
        .options(selectinload(Article.category))
    )
    if article is None:
        raise ContentError("ARTICLE_NOT_FOUND", "Article not found")
    return article


def create_article(
    db: Session,
    payload: ArticleCreate,
    author: User,
) -> Article:
    if db.scalar(select(Article).where(Article.slug == payload.slug)):
        raise ContentError("ARTICLE_SLUG_EXISTS", "An article with this slug exists")
    if payload.category_id is not None:
        _require_category(db, payload.category_id)
    values = payload.model_dump()
    values["author_id"] = author.id
    if values["status"] == "published":
        values["published_at"] = datetime.now(timezone.utc)
    article = Article(**values)
    db.add(article)
    db.commit()
    return get_manageable_article(db, article.id)


def update_article(
    db: Session,
    article_id: UUID,
    payload: ArticleUpdate,
) -> Article:
    article = db.scalar(
        select(Article)
        .where(Article.id == article_id)
        .options(selectinload(Article.category))
    )
    if article is None:
        raise ContentError("ARTICLE_NOT_FOUND", "Article not found")
    values = payload.model_dump(exclude_unset=True)
    if "slug" in values:
        existing = db.scalar(
            select(Article).where(
                Article.slug == values["slug"],
                Article.id != article_id,
            )
        )
        if existing:
            raise ContentError("ARTICLE_SLUG_EXISTS", "An article with this slug exists")
    if "category_id" in values and values["category_id"] is not None:
        _require_category(db, values["category_id"])
    if "status" in values:
        if values["status"] == "published" and article.published_at is None:
            values["published_at"] = datetime.now(timezone.utc)
        if values["status"] == "archived":
            values["published_at"] = None
    for field, value in values.items():
        setattr(article, field, value)
    db.commit()
    return get_manageable_article(db, article.id)


def _require_category(db: Session, category_id: UUID) -> None:
    if db.get(Category, category_id) is None:
        raise ContentError("CATEGORY_NOT_FOUND", "Category not found")
