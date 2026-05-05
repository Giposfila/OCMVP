from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+psycopg2://verifyai:verifyai@localhost:5432/verifyai_db"

    # Application
    secret_key: str = "change-me-in-production-must-be-at-least-32-chars"
    app_env: str = "development"
    debug: bool = False
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    # amoCRM
    amo_domain: str = ""
    amo_access_token: str = ""
    amo_refresh_token: str = ""
    amo_client_id: str = ""
    amo_client_secret: str = ""
    amo_redirect_uri: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()
