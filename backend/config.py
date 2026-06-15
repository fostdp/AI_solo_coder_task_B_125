from pydantic_settings import BaseSettings
from typing import List
from pydantic import field_validator


class Settings(BaseSettings):
    app_name: str = "应县木塔健康监测系统"
    app_version: str = "1.0.0"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000

    database_url: str
    timescaledb_url: str
    redis_url: str

    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    data_retention_days: int = 365
    alert_check_interval: int = 60
    simulation_timeout: int = 300

    cors_origins: str = "*"

    @field_validator('cors_origins')
    @classmethod
    def parse_cors_origins(cls, v) -> List[str]:
        if isinstance(v, list):
            return v
        if v == "*":
            return ["*"]
        return [origin.strip() for origin in v.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
