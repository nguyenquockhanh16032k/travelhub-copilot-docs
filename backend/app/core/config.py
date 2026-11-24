from functools import lru_cache
import json
from typing import Annotated, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "TravelHub API"
    environment: Literal["development", "test", "production"] = "development"
    database_url: str = "postgresql+psycopg://travelhub:change_this_local_password@db:5432/travelhub"
    cors_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:5173",
        "http://localhost:5174",
    ]
    jwt_secret_key: str = "replace_with_a_long_random_secret"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7
    booking_pending_hold_minutes: int = 30
    business_timezone: str = "Asia/Ho_Chi_Minh"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("booking_pending_hold_minutes")
    @classmethod
    def validate_booking_pending_hold_minutes(cls, value: int) -> int:
        if value < 1:
            raise ValueError("BOOKING_PENDING_HOLD_MINUTES must be at least 1")
        return value

    @field_validator("business_timezone")
    @classmethod
    def validate_business_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ValueError, ZoneInfoNotFoundError) as exc:
            raise ValueError("BUSINESS_TIMEZONE must be a valid IANA timezone") from exc
        return value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("["):
                return json.loads(stripped)
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def validate_production_jwt_secret(self) -> "Settings":
        if self.environment == "production" and (
            self.jwt_secret_key == "replace_with_a_long_random_secret"
            or len(self.jwt_secret_key) < 32
        ):
            raise ValueError(
                "Production requires a unique JWT_SECRET_KEY with at least 32 characters"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
