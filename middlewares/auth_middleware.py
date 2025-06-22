from aiogram.types import TelegramObject
from aiogram import BaseMiddleware
from typing import Callable, Awaitable, Dict, Any


class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Здесь могла бы быть проверка авторизации пользователя
        return await handler(event, data)
