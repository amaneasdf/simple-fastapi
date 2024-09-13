from functools import lru_cache
from pydantic import BaseModel, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class TelemetryConfig(BaseModel):
    enabled: bool = Field(default=False)
    verbose_tracing: bool = Field(default=False)
    trace_sqlalchemy: bool = Field(default=False)

    ingest_endpoint: str = Field(default="")

    api_header: str = Field(default="")
    api_key: str = Field(default="")


class LoggingConfig(BaseModel):
    level: str = Field(default="INFO")

    agent_enabled: bool = Field(default=False)
    agent_host: str = Field(default="localhost")
    agent_port: int = Field(default=5000)


class Settings(BaseSettings):
    app_environment: str = "local"
    app_name: str = "FastAPI Test"

    service_name: str = "fastapitest"
    instance_id: str = "1"

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
    telemetry: TelemetryConfig = Field(default=TelemetryConfig())

    # Logging settings
    logging: LoggingConfig = Field(default=LoggingConfig())

    # Make sure to create a new .env in the project root and set the values
    model_config = SettingsConfigDict(env_file=".env", env_nested_delimiter=".")


@lru_cache
def get_settings() -> Settings:
    return Settings()
