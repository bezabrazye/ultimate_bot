# middlewares/user_middleware.py

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from typing import Callable, Dict, Any, Awaitable
from database.repositories import UserRepository


class UserMiddleware(BaseMiddleware):
    def __init__(self, user_repo: UserRepository):
        super().__init__()
        self.user_repo = user_repo

    async def __call__(self,
                       handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
                       event: TelegramObject,
                       data: Dict[str, Any]) -> Any:
        telegram_user = data.get("event_from_user")
        if telegram_user:
            user = await self.user_repo.get_or_create_user(user_id=telegram_user.id)
            data["user"] = user
        return await handler(event, data)
