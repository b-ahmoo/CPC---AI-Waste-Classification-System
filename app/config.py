import os

from dotenv import load_dotenv

load_dotenv()  # reads .env when running without Docker (Docker passes it via env_file)


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    TEMPLATES_AUTO_RELOAD = True

    # Shared database. An empty DATABASE_URL falls back to a local SQLite file.
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or "sqlite:///waste_assistant.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 11 * 1024 * 1024  # uploads above ~10 MB are rejected