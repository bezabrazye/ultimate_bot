from aiogram_i18n.middleware import I18nMiddleware
from typing import Callable, Awaitable, Dict, Any
from aiogram.types import TelegramObject


class UserI18nMiddleware(I18nMiddleware):
    async def get_locale(
        self,
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> str:
        return "ru"  # Или 'en', если хочешь по умолчанию английский
