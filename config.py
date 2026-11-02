import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Flask
    SECRET_KEY = os.getenv("SECRET_KEY")

    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True
    }


    # JWT
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

    JWT_ACCESS_TOKEN_EXPIRES = 3600
    CLOUDFLARE_WORKER_URL = os.getenv("CLOUDFLARE_WORKER_URL", "").strip()
    WINAY_API_KEY = os.getenv("WINAY_API_KEY", "").strip()

    CORS_ORIGINS = [origin.strip() for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://192.168.0.19:5173,https://localhost"
    ).split(",") if origin.strip()]
