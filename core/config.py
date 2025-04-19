from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    server_bind: str = "0.0.0.0"
    server_port: int | None = 8000
    server_secret_key: str = "vrau-easter-egg"
    server_debug: bool = False
    server_access_token_expire_minutes: int = 60 * 24 * 7
    server_algorithm: str = "HS256"

    server_endpoint: str = "lara-bomb-api.insper.dev"
    server_endpoint_ssl: bool = True

    client_title: str = "Lara Bomb"
    client_width: int = 800
    client_height: int = 600
    client_fps: int = 60

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()


def get_settings() -> Settings:
    return settings
