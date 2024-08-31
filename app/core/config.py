from functools import lru_cache
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_environment: str = "local"
    app_name: str = "FastAPI Test"

    # Initial admin username and password
    first_admin_username: str = "admin"
    first_admin_password: SecretStr = Field(default="admin")

    # Database settings
    database_host: str = "localhost"
    database_port: int = 3306
    database_name: str = "fastapitest"
    database_username: str = "root"
    database_password: SecretStr = Field(default="")

    @property
    def database_url(self):
        return f"mysql+pymysql://{self.database_username}:{self.database_password.get_secret_value()}@{self.database_host}:{self.database_port}/{self.database_name}"

    # JWT settings
    secret_key: SecretStr = Field(default="secret")
    algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=60)

    # OpenTelemetry settings
    telemetry_enabled: bool = Field(default=False)
    verbose_tracing: bool = Field(default=False)
    trace_sqlalchemy: bool = Field(default=False)
    telemetry_endpoint: str = Field(default="")
    telemetry_api_header: str = Field(default="")
    telemetry_api_key: str = Field(default="")

    # Make sure to create a new .env in the project root and set the values
    model_config = SettingsConfigDict(env_file=".env")


@lru_cache
def get_settings() -> Settings:
    return Settings()
