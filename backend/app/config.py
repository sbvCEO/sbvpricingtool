from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SANCNIDA API"
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_audience: str = "sancnida-api"
    jwt_issuer: str = "sancnida-auth"
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/1"
    async_fallback_local: bool = True
    database_url: str = ""
    admin_store_backend: str = "memory"
    cpq_store_backend: str = "memory"

    model_config = SettingsConfigDict(env_prefix="APP_", case_sensitive=False)


settings = Settings()
