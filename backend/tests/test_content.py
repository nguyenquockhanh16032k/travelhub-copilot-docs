from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_current_user
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.identity import Role, User


@pytest.fixture
def content_context():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        author = User(
            email="editor@example.com",
            password_hash="not-used",
            is_active=True,
        )
        session.add(author)
        session.commit()
        author_id = author.id

    def override_db():
        with Session(engine) as session:
            yield session

    admin = SimpleNamespace(
        id=author_id,
        email="editor@example.com",
        roles=[Role(code="ADMIN", description="Administrator")],
    )
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: admin

    with TestClient(app) as client:
        yield client, engine

    app.dependency_overrides.clear()
    engine.dispose()


def test_staff_can_create_category_and_article(content_context) -> None:
    client, _ = content_context

    category = client.post(
        "/api/v1/categories",
        json={"name": "Travel tips", "slug": "travel-tips"},
    )
    assert category.status_code == 201
    category_id = category.json()["id"]

    article = client.post(
        "/api/v1/articles",
        json={
            "title": "Packing for Da Lat",
            "slug": "packing-for-da-lat",
            "body": "Bring a light jacket.",
            "category_id": category_id,
            "cover_image_url": "https://example.com/cover.jpg",
            "status": "published",
            "seo_title": "Packing guide",
            "seo_description": "What to pack for Da Lat",
        },
    )
    assert article.status_code == 201
    assert article.json()["status"] == "published"
    assert article.json()["category"]["slug"] == "travel-tips"
    assert article.json()["published_at"] is not None

    public_list = client.get("/api/v1/articles")
    assert public_list.status_code == 200
    assert public_list.json()["total"] == 1

    public_detail = client.get("/api/v1/articles/packing-for-da-lat")
    assert public_detail.status_code == 200
    assert public_detail.json()["title"] == "Packing for Da Lat"


def test_article_slug_must_be_unique_and_public_hides_drafts(
    content_context,
) -> None:
    client, _ = content_context

    first = client.post(
        "/api/v1/articles",
        json={
            "title": "Draft article",
            "slug": "draft-article",
            "body": "Not public yet.",
            "status": "draft",
        },
    )
    assert first.status_code == 201

    duplicate = client.post(
        "/api/v1/articles",
        json={
            "title": "Another title",
            "slug": "draft-article",
            "body": "Duplicate slug.",
            "status": "draft",
        },
    )
    assert duplicate.status_code == 409

    public_list = client.get("/api/v1/articles")
    assert public_list.json()["total"] == 0
    assert client.get("/api/v1/articles/draft-article").status_code == 404

    admin_list = client.get("/api/v1/admin/articles")
    assert admin_list.status_code == 200
    assert admin_list.json()["total"] == 1


def test_publishing_then_archiving_controls_publication_time(
    content_context,
) -> None:
    client, _ = content_context

    created = client.post(
        "/api/v1/articles",
        json={
            "title": "Lifecycle",
            "slug": "lifecycle",
            "body": "Article lifecycle.",
        },
    )
    article_id = created.json()["id"]

    published = client.patch(
        f"/api/v1/articles/{article_id}",
        json={"status": "published"},
    )
    assert published.status_code == 200
    assert published.json()["published_at"] is not None

    archived = client.patch(
        f"/api/v1/articles/{article_id}",
        json={"status": "archived"},
    )
    assert archived.status_code == 200
    assert archived.json()["published_at"] is None
    assert client.get("/api/v1/articles/lifecycle").status_code == 404


def test_content_management_requires_staff_role(content_context) -> None:
    client, _ = content_context
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        roles=[Role(code="CUSTOMER", description="Customer")]
    )

    assert client.get("/api/v1/admin/articles").status_code == 403
    assert client.post(
        "/api/v1/categories",
        json={"name": "Forbidden", "slug": "forbidden"},
    ).status_code == 403
