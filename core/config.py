from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    host: str = "lara-bomb.insper.dev"
    port: int | None = 8000
    secret_key: str = "vrau-easter-egg"

    class Config:
        env_file = ".env"


settings = Settings()


def get_settings() -> Settings:
    return settings
