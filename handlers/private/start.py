# handlers/private/start.py
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from typing import Callable, Optional

from database.models import User
from database.repositories import UserRepository
from utils.keyboards import get_language_kb, get_main_menu_kb
from utils.states import Form
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, user: User, user_repo: UserRepository, _: Callable[[str], str]):
    await state.clear() # Clear any previous FSM states

    referrer_id = None
    if len(message.text.split()) > 1:
        try:
            # Extract referrer ID from /start payload (e.g., /start 123456)
            payload = message.text.split()[1]
            if payload.isdigit():
                referrer_id = int(payload)
                # If referrer exists and it's not self-referral, assign it
                if referrer_id != user.id:
                    existing_referrer = await user_repo.get_user_by_id(referrer_id)
                    if existing_referrer and not user.referrer_id: # Only set if not already set
                        await user_repo.update_user(user.id, {"referrer_id": referrer_id})
                        await user_repo.increment({"_id": referrer_id}, "referred_users_count")
                        logger.info(f"User {user.id} was referred by {referrer_id}")
                        user.referrer_id = referrer_id # Update in-memory user
                else:
                    logger.warning(f"User {user.id} tried to self-refer.")
            elif payload.startswith('@'): # Assuming referrers can be usernames too
                # Find referrer by username
                referrer_user = await user_repo.get_one({"username": payload[1:]})
                if referrer_user and referrer_user.id != user.id:
                    if not user.referrer_id:
                        await user_repo.update_user(user.id, {"referrer_id": referrer_user.id})
                        await user_repo.increment({"_id": referrer_user.id}, "referred_users_count")
                        logger.info(f"User {user.id} was referred by {referrer_user.id} (@{payload[1:]})")
                        user.referrer_id = referrer_user.id
                else:
                    logger.warning(f"User {user.id} tried to self-refer or invalid referrer username: {payload}")

        except ValueError:
            logger.warning(f"Invalid start payload format for user {user.id}: {message.text}")

    if user.is_banned:
        await message.answer(_("common.access_denied"))
        return

    admin_status_msg = ""
    if user.id in settings.ADMIN_IDS:
        admin_status_msg = _("admin_panel.access_granted") # Admins get a special greeting
        
    greeting_text = _("main_menu.greeting").format(user_name=user.first_name or user.username or "друг")

    if not user.lang_code:
        # First time user or language not set
        await message.answer(_("language_selection.prompt"), reply_markup=get_language_kb())
        await state.set_state(Form.lang_selection)
    elif not user.channels and not user.is_admin: # If no channels added and not admin (admins can bypass channel setup)
        await message.answer(greeting_text + "\n" + _("initial_channel_setup.prompt"))
        await state.set_state(Form.channel_link_input)
    else:
        # User already set up language and channels/is admin
        await message.answer(f"{greeting_text}\n{admin_status_msg}", reply_markup=get_main_menu_kb(_))
