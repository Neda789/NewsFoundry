import os


class Settings:
    """Centralise la lecture des variables d'environnement du projet."""

    database_url: str = os.getenv("DATABASE_URL", "")
    worldnews_api_key: str = os.getenv("WORLDNEWS_API_KEY", "")
    mistral_api_key: str = os.getenv("MISTRAL_API_KEY", "")


settings = Settings()
