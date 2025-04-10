from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    host: str = "lara-bomb.insper.dev"
    port: int | None = 8000
    secret_key: str = "vrau-easter-egg"
    debug: bool = False
    access_token_expire_minutes: int = 60 * 24 * 7
    algorithm: str = "HS256"

    title: str = "Lara Bomb"
    width: int = 800
    height: int = 600
    fps: int = 60

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()


def get_settings() -> Settings:
    return settings
