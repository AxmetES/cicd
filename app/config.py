import os

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET: str
    GMAIL_USER: str
    GMAIL_APP_PASSWORD: str
    FRONTEND_URL: str

    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_BUCKET: str

    model_config = SettingsConfigDict(env_file=os.path.join(BASE_DIR, ".env"))

settings = Settings()