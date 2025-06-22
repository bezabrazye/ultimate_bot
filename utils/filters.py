# utils/filters.py
from aiogram.filters import Filter
from aiogram.types import Message
from config.settings import settings
from database.models import User # For type hinting in handler

class AdminFilter(Filter):
    async def __call__(self, message: Message, user: User) -> bool:
        return user.is_admin

2.9 utils/misc.py
# utils/misc.py
import re
from typing import Optional, Any
from datetime import datetime
from aiogram.exceptions import TelegramBadRequest

def is_valid_telegram_link(link: str) -> bool:
    """Checks if the given string is a valid Telegram channel/group link format."""
    # Examples: https://t.me/channel, @channel, t.me/channel, https://t.me/+invitecode
    regex = r"^(https?://)?(t\.me|telegram\.me)/([a-zA-Z0-9_-]+|joinchat/[a-zA-Z0-9_-]+)$|^@([a-zA-Z0-9_]{5,32})$"
    return bool(re.match(regex, link))

def extract_username_from_link(link: str) -> Optional[str]:
    """Extracts username from Telegram link."""
    match = re.search(r"(?:https?://)?(?:t\.me|telegram\.me)/([a-zA-Z0-9_]{5,32})(?:/?(?:joinchat)?(?:/)?([a-zA-Z0-9_-]+)?)?|^@([a-zA-Z0-9_]{5,32})$", link)
    if match:
        if match.group(1): # t.me/username or t.me/joinchat/code
            # This is tricky because joinchat doesn't give a username. We need chat ID.
            # For simplicity, if it's not a common username pattern, we assume it's private or invalid for direct lookup.
            if match.group(1).lower() == 'joinchat':
                return None # Cannot extract username from joinchat link directly
            return match.group(1)
        if match.group(3): # @username
            return match.group(3)
    return None

def format_datetime(dt: datetime, lang_code: str = "en") -> str:
    """Formats datetime object for display."""
    if lang_code == "ru":
        return dt.strftime("%d.%m.%Y %H:%M:%S")
    return dt.strftime("%Y-%m-%d %H:%M:%S")

async def safe_send_message(bot, chat_id: int, text: str, **kwargs: Any) -> None:
    """
    Safely sends a message, catching common Telegram API errors (e.g., bot blocked by user).
    """
    try:
        await bot.send_message(chat_id, text, **kwargs)
    except TelegramBadRequest as e:
        # User blocked the bot, chat not found, etc.
        if "bot was blocked by the user" in str(e) or "chat not found" in str(e):
            return # Silently ignore for broadcast/mass messaging
        else:
            raise # Re-raise other unexpected errors
    except Exception as e:
        raise # Re-raise other errors
