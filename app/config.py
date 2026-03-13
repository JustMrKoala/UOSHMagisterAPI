from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()