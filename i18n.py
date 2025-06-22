# i18n.py
from pathlib import Path
# --- PATCH START ---
from aiogram_i18n.manager import I18n # Changed: Import I18n from the 'manager' submodule
# --- PATCH END ---
from aiogram_i18n.cores import FluentI18n # This import path remains correct

# --- IMPORTANT PATH CONFIGURATION ---
# This path needs to correctly point to your 'locales' directory.
LOCALES_DIR = Path(__file__).parent / "locales"


i18n_manager = I18n(
    path=LOCALES_DIR,
    default_locale="en", # Set your default language code (e.g., "en", "ru")
    core=FluentI18n(path=LOCALES_DIR) # Use FluentI18n for .ftl files
)
