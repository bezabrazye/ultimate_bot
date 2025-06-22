# config/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from typing import List, Optional

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', secrets_dir='/run/secrets/')

    # Base bot config
    BOT_TOKEN: str
    ADMIN_IDS: List[int] = [] # Set default empty list, will be populated from .env

    # MongoDB
    MONGO_URI: str
    MONGO_DB_NAME: str

    # Cryptomus API
    CRYPTOMUS_MERCHANT_ID: str
    CRYPTOMUS_API_KEY: str
    CRYPTOMUS_WEBHOOK_SECRET: str

    # AI Service (example for ChatGPT like API)
    OPENAI_API_KEY: Optional[str] = None # Optional, as AI analysis is PRO feature

    # Telegram Mini App Settings
    WEBAPP_BASE_URL: str # Base URL where your webapp backend is hosted (e.g., ngrok URL)
    WEBAPP_API_URL: str  # Full URL to your webapp API endpoint for data submission
    WEBAPP_FRONTEND_PATH: str # Path to access index.html (e.g., /web-app)
    WEBAPP_INITDATA_SECRET: str # Secret key for validating Telegram WebApp initData

    # Telethon/Pyrogram (for userbots, not directly used by this bot's core logic)
    TG_API_ID: Optional[int] = None
    TG_API_HASH: Optional[str] = None

    # Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    LOCALES_DIR: Path = BASE_DIR / "i18n" / "locales"

# Initialize settings
settings = Settings()
