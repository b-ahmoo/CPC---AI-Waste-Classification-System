"""App configuration. Placeholder so the app can start; extend as needed."""

import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
