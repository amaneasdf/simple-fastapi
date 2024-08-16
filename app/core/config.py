from functools import lru_cache
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_environment: str = "local"
    app_name: str = "FastAPI Test"

    # Initial admin username and password
    first_admin_username: str = "admin"
    first_admin_password: SecretStr = "admin"  # type: ignore

    # Database settings
    database_host: str = "localhost"
    database_port: int = 3306
    database_name: str = "fastapitest"
    database_username: str = "root"
    database_password: SecretStr = ""  # type: ignore

    @property
    def database_url(self):
        return f"mysql+pymysql://{self.database_username}:{self.database_password.get_secret_value()}@{self.database_host}:{self.database_port}/{self.database_name}"

    # Make sure to create a new .env in the project root and set the values
    model_config = SettingsConfigDict(env_file=".env")


@lru_cache
def get_settings() -> Settings:
    return Settings()
