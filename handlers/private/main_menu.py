# handlers/private/main_menu.py
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from typing import Callable

from database.models import User
from utils.keyboards import get_main_menu_kb, get_boosting_menu_kb, get_account_menu_kb, get_wallet_menu_kb, get_offers_menu_kb
from utils.callbacks import MainMenuCallback
import logging

logger = logging.getLogger(__name__)

router = Router()

@router.message(F.text)
async def handle_main_menu_buttons(message: Message, state: FSMContext, user: User, _: Callable[[str], str]):
    await state.clear() # Clear FSM state when returning to main menu

    if message.text == _("main_menu.buttons.boosting"):
        await message.answer(_("main_menu.buttons.boosting"), reply_markup=get_boosting_menu_kb(_))
    elif message.text == _("main_menu.buttons.my_account"):
        # This duplicates logic in callbacks.py but ensures direct button press works
        pro_status_text = _("my_account_menu.pro_status_inactive")
        if user.is_pro:
            pro_status_text = _("my_account_menu.pro_status_active")
            if user.pro_expires_at:
                pro_status_text += _("my_account_menu.pro_expires").format(date=user.pro_expires_at.strftime("%Y-%m-%d"))

        user_info = _("my_account_menu.user_info").format(
            id=user.id,
            username=user.username or "N/A",
            first_name=user.first_name or "",
            last_name=user.last_name or "",
            lang_code=user.lang_code or "N/A",
            registered_at=user.registered_at.strftime("%Y-%m-%d %H:%M"),
            last_activity_at=user.last_activity_at.strftime("%Y-%m-%d %H:%M"),
            balance=user.balance,
            pro_status_text=pro_status_text
        )
        await message.answer(user_info, reply_markup=get_account_menu_kb(_))
    elif message.text == _("main_menu.buttons.wallet"):
        await message.answer(_("wallet_menu.current_balance").format(balance=user.balance), reply_markup=get_wallet_menu_kb(_))
    elif message.text == _("main_menu.buttons.offers"):
        await message.answer(_("offers_menu.offers_title"), reply_markup=get_offers_menu_kb(_))
    else:
        # Fallback for unrecognized text commands
        await message.answer(_("main_menu.greeting").format(user_name=message.from_user.first_name or message.from_user.username), reply_markup=get_main_menu_kb(_))