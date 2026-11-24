from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.core.permissions import Permission
from app.db.session import get_db
from app.models.identity import User
from app.schemas.content import (
    ArticleCreate,
    ArticlePage,
    ArticleResponse,
    ArticleUpdate,
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
)
from app.services.content_service import (
    ContentError,
    create_article,
    create_category,
    get_manageable_article,
    get_published_article,
    list_articles,
    list_categories,
    update_article,
    update_category,
)


router = APIRouter(tags=["content"])
can_read_articles = require_permission(Permission.ARTICLES_READ)
can_write_articles = require_permission(Permission.ARTICLES_WRITE)


def content_error(exc: ContentError) -> HTTPException:
    status_code = status.HTTP_404_NOT_FOUND
    if exc.code in {"CATEGORY_SLUG_EXISTS", "ARTICLE_SLUG_EXISTS"}:
        status_code = status.HTTP_409_CONFLICT
    return HTTPException(
        status_code=status_code,
        detail={"code": exc.code, "message": exc.message},
    )


@router.get("/categories", response_model=list[CategoryResponse])
def read_categories(db: Session = Depends(get_db)) -> list[CategoryResponse]:
    return [
        CategoryResponse.model_validate(category)
        for category in list_categories(db)
    ]


@router.post(
    "/categories",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_category(
    payload: CategoryCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(can_write_articles),
) -> CategoryResponse:
    try:
        return CategoryResponse.model_validate(create_category(db, payload))
    except ContentError as exc:
        raise content_error(exc) from None


@router.patch("/categories/{category_id}", response_model=CategoryResponse)
def patch_category(
    category_id: UUID,
    payload: CategoryUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(can_write_articles),
) -> CategoryResponse:
    try:
        return CategoryResponse.model_validate(
            update_category(db, category_id, payload)
        )
    except ContentError as exc:
        raise content_error(exc) from None


@router.get("/articles", response_model=ArticlePage)
def read_articles(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, max_length=255),
    category_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
) -> ArticlePage:
    items, total, pages = list_articles(
        db,
        page,
        size,
        search,
        published_only=True,
        category_id=category_id,
    )
    return ArticlePage(
        items=[ArticleResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


@router.get("/articles/{slug}", response_model=ArticleResponse)
def read_article(slug: str, db: Session = Depends(get_db)) -> ArticleResponse:
    try:
        return ArticleResponse.model_validate(get_published_article(db, slug))
    except ContentError as exc:
        raise content_error(exc) from None


@router.get("/admin/articles", response_model=ArticlePage)
def read_manageable_articles(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, max_length=255),
    db: Session = Depends(get_db),
    _user: User = Depends(can_read_articles),
) -> ArticlePage:
    items, total, pages = list_articles(
        db,
        page,
        size,
        search,
        published_only=False,
    )
    return ArticlePage(
        items=[ArticleResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


@router.get("/admin/articles/{article_id}", response_model=ArticleResponse)
def read_manageable_article(
    article_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(can_read_articles),
) -> ArticleResponse:
    try:
        return ArticleResponse.model_validate(
            get_manageable_article(db, article_id)
        )
    except ContentError as exc:
        raise content_error(exc) from None


@router.post(
    "/articles",
    response_model=ArticleResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_article(
    payload: ArticleCreate,
    db: Session = Depends(get_db),
    user: User = Depends(can_write_articles),
) -> ArticleResponse:
    try:
        return ArticleResponse.model_validate(create_article(db, payload, user))
    except ContentError as exc:
        raise content_error(exc) from None


@router.patch("/articles/{article_id}", response_model=ArticleResponse)
def patch_article(
    article_id: UUID,
    payload: ArticleUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(can_write_articles),
) -> ArticleResponse:
    try:
        return ArticleResponse.model_validate(
            update_article(db, article_id, payload)
        )
    except ContentError as exc:
        raise content_error(exc) from None
