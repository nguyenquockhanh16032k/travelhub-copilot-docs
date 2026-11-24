from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


ArticleStatus = Literal["draft", "published", "archived"]


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(
        min_length=1,
        max_length=255,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )


class CategoryResponse(BaseModel):
    id: UUID
    name: str
    slug: str

    model_config = {"from_attributes": True}


class ArticleCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    slug: str = Field(
        min_length=1,
        max_length=255,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )
    body: str = Field(min_length=1)
    category_id: UUID | None = None
    cover_image_url: str | None = Field(default=None, max_length=2048)
    status: ArticleStatus = "draft"
    seo_title: str | None = Field(default=None, max_length=255)
    seo_description: str | None = Field(default=None, max_length=5000)


class ArticleUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )
    body: str | None = Field(default=None, min_length=1)
    category_id: UUID | None = None
    cover_image_url: str | None = Field(default=None, max_length=2048)
    status: ArticleStatus | None = None
    seo_title: str | None = Field(default=None, max_length=255)
    seo_description: str | None = Field(default=None, max_length=5000)


class ArticleResponse(BaseModel):
    id: UUID
    category_id: UUID | None
    author_id: UUID | None
    title: str
    slug: str
    body: str
    cover_image_url: str | None
    status: ArticleStatus
    seo_title: str | None
    seo_description: str | None
    published_at: datetime | None
    category: CategoryResponse | None

    model_config = {"from_attributes": True}


class ArticlePage(BaseModel):
    items: list[ArticleResponse]
    total: int
    page: int
    size: int
    pages: int
