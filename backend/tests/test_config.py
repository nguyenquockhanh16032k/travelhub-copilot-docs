import json

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_parse_comma_separated_cors_origins(monkeypatch) -> None:
    monkeypatch.setenv(
        "CORS_ORIGINS",
        "http://localhost:5173, http://localhost:5174",
    )

    settings = Settings(_env_file=None)

    assert settings.cors_origins == [
        "http://localhost:5173",
        "http://localhost:5174",
    ]


def test_settings_parse_json_cors_origins(monkeypatch) -> None:
    expected = ["https://admin.example.com", "https://app.example.com"]
    monkeypatch.setenv("CORS_ORIGINS", json.dumps(expected))

    settings = Settings(_env_file=None)

    assert settings.cors_origins == expected


def test_production_settings_reject_placeholder_jwt_secret() -> None:
    with pytest.raises(
        ValidationError,
        match="Production requires a unique JWT_SECRET_KEY",
    ):
        Settings(
            _env_file=None,
            environment="production",
            jwt_secret_key="replace_with_a_long_random_secret",
        )


def test_production_settings_accept_configured_jwt_secret() -> None:
    settings = Settings(
        _env_file=None,
        environment="production",
        jwt_secret_key="unique-production-signing-key-with-adequate-length",
    )

    assert (
        settings.jwt_secret_key
        == "unique-production-signing-key-with-adequate-length"
    )


def test_production_settings_reject_short_jwt_secret() -> None:
    with pytest.raises(
        ValidationError,
        match="Production requires a unique JWT_SECRET_KEY",
    ):
        Settings(
            _env_file=None,
            environment="production",
            jwt_secret_key="too-short",
        )


def test_settings_reject_invalid_business_timezone() -> None:
    with pytest.raises(ValidationError, match="valid IANA timezone"):
        Settings(_env_file=None, business_timezone="Not/A_Timezone")
