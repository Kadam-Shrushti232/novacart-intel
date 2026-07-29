from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    api_key: str
    openrouter_api_key: str
    chroma_persist_directory: str = "./chroma_data"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
