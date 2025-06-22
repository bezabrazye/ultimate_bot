# handlers/private/offers.py
from aiogram import Router, F
from aiogram.types import CallbackQuery
from typing import Callable

from utils.keyboards import get_offers_menu_kb, get_main_menu_kb
from utils.callbacks import MainMenuCallback

router = Router()

@router.callback_query(MainMenuCallback.filter(F.action == "become_pro"))
async def become_pro_offer(call: CallbackQuery, _: Callable[[str], str]):
    await call.message.edit_text(_("offers_menu.pro_info"), reply_markup=get_offers_menu_kb(_))
    await call.answer()

@router.callback_query(MainMenuCallback.filter(F.action == "franchise"))
async def franchise_offer(call: CallbackQuery, _: Callable[[str], str]):
    await call.message.edit_text(_("offers_menu.franchise_info"), reply_markup=get_offers_menu_kb(_))
    await call.answer()
