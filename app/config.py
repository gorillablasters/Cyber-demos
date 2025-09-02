from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, field_validator
from typing import List


class Settings(BaseSettings):
    DATABASE_URL: str
    ENV: str = "dev"
    CORS_ORIGINS: List[AnyHttpUrl] | List[str] = ["http://localhost:3000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def split_csv(cls, v):
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v

    class Config:
        env_file = ".env"


settings = Settings()
