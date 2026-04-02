from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    DATABASE_URL: str = (
        "postgresql+asyncpg://palavracadabra:palavracadabra@localhost:5432/palavracadabra"
    )

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Auth / JWT
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    ALGORITHM: str = "HS256"

    # AWS
    AWS_REGION: str = "us-east-1"
    AWS_S3_BUCKET: str = "palavracadabra-assets"
    COGNITO_USER_POOL_ID: str = ""
    COGNITO_CLIENT_ID: str = ""

    # Anthropic / Claude
    ANTHROPIC_API_KEY: str = ""

    # App
    APP_NAME: str = "Palavra Cadabra API"
    DEBUG: bool = False

    # CORS
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:63469",
    ]
    # In dev, allow any localhost port for Flutter web dev server
    CORS_ALLOW_ALL_LOCALHOST: bool = True


settings = Settings()
