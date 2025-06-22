# handlers/private/account.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from typing import Callable

from database.models import User
from services.user_service import UserService
from utils.keyboards import get_account_menu_kb, get_promocode_menu_kb, get_main_menu_kb
from utils.callbacks import MainMenuCallback, PromocodeCallback
from utils.states import Form
import logging

logger = logging.getLogger(__name__)

router = Router()

@router.callback_query(MainMenuCallback.filter(F.action == "promocode"))
async def show_promocode_menu(call: CallbackQuery, _: Callable[[str], str]):
    await call.message.edit_text(_("my_account_menu.promocode_title"), reply_markup=get_promocode_menu_kb(_))
    await call.answer()

@router.callback_query(PromocodeCallback.filter(F.action == "input"))
async def input_promocode(call: CallbackQuery, state: FSMContext, _: Callable[[str], str]):
    await call.message.edit_text(_("my_account_menu.enter_promocode"))
    await state.set_state(Form.input_promocode)
    await call.answer()

@router.message(Form.input_promocode, F.text)
async def process_promocode_input(message: Message, state: FSMContext, user: User, user_service: UserService, _: Callable[[str], str]):
    promocode_text = message.text.strip().upper()

    promo = await user_service.apply_promo_code(user, promocode_text)

    if promo:
        await message.answer(_("my_account_menu.promocode_applied").format(code=promo.name, credits=promo.credits), reply_markup=get_main_menu_kb(_))
        # Update user's balance in memory correctly as service updates it in DB
        user.balance += promo.credits
    elif user.warnings > 0 and user.is_banned: # Specific message for ban
         await message.answer(_("my_account_menu.promocode_fraud_banned"), reply_markup=get_main_menu_kb(_)) # Needs new locale key
    elif user.warnings > 0:
        await message.answer(_("my_account_menu.promocode_fraud"), reply_markup=get_main_menu_kb(_))
    else:
        await message.answer(_("my_account_menu.promocode_invalid"), reply_markup=get_main_menu_kb(_))

    await state.clear()

@router.callback_query(MainMenuCallback.filter(F.action == "invite_friends"))
async def show_invite_friends(call: CallbackQuery, user: User, _: Callable[[str], str]):
    referral_link = f"https://t.me/{call.bot.username}?start={user.id}" # User ID as referral code
    
    # You might want to format the stats more nicely if numbers get large
    referral_stats_text = _("my_account_menu.referral_stats").format(
        invited_count=user.referred_users_count,
        paid_count=user.referred_users_paid_count,
        earned_credits=user.earned_referral_credits
    )

    response_text = _("my_account_menu.referral_link").format(link=referral_link) + "\n\n" + referral_stats_text
    
    await call.message.edit_text(response_text, reply_markup=get_account_menu_kb(_))
    await call.answer()

# No specific handler needed for WebApp button, as it opens a URL directly.
# The WebApp will then communicate with your backend.
