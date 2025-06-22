# handlers/private/channel_setup.py
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from typing import Callable, Any

from database.models import User, Channel
from services.channel_service import ChannelService
from utils.states import Form
from utils.keyboards import get_main_menu_kb
import logging

logger = logging.getLogger(__name__)

router = Router()

@router.message(Form.channel_link_input, F.text)
async def process_channel_link(message: Message, state: FSMContext, user: User, channel_service: ChannelService, _: Callable[[str], str]):
    channel_link = message.text.strip()

    # Pass the user object to the service method
    channel, error_code, subs_count = await channel_service.verify_and_add_channel(user, channel_link)

    if error_code == "success":
        await message.answer(_("initial_channel_setup.success").format(channel_title=channel.title), reply_markup=get_main_menu_kb(_))
        await state.clear()
    elif error_code == "invalid_link":
        await message.answer(_("initial_channel_setup.invalid_link"))
    elif error_code == "invalid_link_no_username" or error_code == "telegram_api_error":
        await message.answer(_("initial_channel_setup.error_checking_channel"))
    elif error_code == "not_channel_or_group":
        await message.answer(_("initial_channel_setup.invalid_link")) # Generic for now
    elif error_code == "bot_not_admin_or_permissions":
        await message.answer(_("initial_channel_setup.bot_not_admin_or_permissions"))
    elif error_code == "not_owner":
        await message.answer(_("initial_channel_setup.not_owner"))
    elif error_code == "not_enough_subscribers":
        await message.answer(_("initial_channel_setup.not_enough_subscribers").format(count=subs_count))
    elif error_code == "channel_already_added":
        await message.answer(_("initial_channel_setup.channel_already_added"), reply_markup=get_main_menu_kb(_))
        await state.clear()
    elif error_code == "max_channels_reached":
        await message.answer(_("initial_channel_setup.max_channels_reached").format(max_slots=user.max_channels_slots))
    else:
        await message.answer(_("error.default"))
        logger.error(f"Unknown error during channel setup for user {user.id}: {error_code}")

# Handle other message types that might incorrectly trigger this state
@router.message(Form.channel_link_input)
async def process_channel_link_invalid_type(message: Message, _: Callable[[str], str]):
    await message.answer(_("initial_channel_setup.invalid_link"))

