import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    TEMPLATES_AUTO_RELOAD = True