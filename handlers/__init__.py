# handlers/__init__.py
# Import all handler modules to ensure their routers are registered when bot.py imports them.
# The actual registration happens in bot.py using dp.include_router()

from . import private
from . import admin
from . import callbacks # Contains common callback handlers

2.25 handlers/callbacks.py (Общие обработчики CallbackData)
# handlers/callbacks.py
from aiogram import Router, F
from aiogram.types import CallbackQuery
from utils.callbacks import MainMenuCallback, BoostOrderCallback, WalletCallback, PromocodeCallback, AdminCallback, AdminReportCallback
from aiogram.fsm.context import FSMContext
from database.models import User
from typing import Callable

router = Router()

@router.callback_query(MainMenuCallback.filter(F.action == "main_menu"))
async def go_to_main_menu(call: CallbackQuery, _: Callable[[str], str]):
    from utils.keyboards import get_main_menu_kb # Lazy import to avoid circular dependency
    await call.message.edit_text(_("main_menu.greeting").format(user_name=call.from_user.first_name or call.from_user.username), reply_markup=None)
    await call.message.answer(_("main_menu.greeting").format(user_name=call.from_user.first_name or call.from_user.username), reply_markup=get_main_menu_kb(_))
    await call.answer()

@router.callback_query(MainMenuCallback.filter(F.action == "boosting"))
async def go_to_boosting_menu(call: CallbackQuery, _: Callable[[str], str]):
    from utils.keyboards import get_boosting_menu_kb
    await call.message.edit_text(_("main_menu.buttons.boosting"), reply_markup=get_boosting_menu_kb(_))
    await call.answer()

@router.callback_query(MainMenuCallback.filter(F.action == "wallet"))
async def go_to_wallet_menu(call: CallbackQuery, _: Callable[[str], str], user: User):
    from utils.keyboards import get_wallet_menu_kb
    await call.message.edit_text(_("wallet_menu.current_balance").format(balance=user.balance), reply_markup=get_wallet_menu_kb(_))
    await call.answer()

@router.callback_query(MainMenuCallback.filter(F.action == "my_account"))
async def go_to_account_menu(call: CallbackQuery, _: Callable[[str], str], user: User):
    from utils.keyboards import get_account_menu_kb
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
    await call.message.edit_text(user_info, reply_markup=get_account_menu_kb(_))
    await call.answer()

@router.callback_query(MainMenuCallback.filter(F.action == "offers"))
async def go_to_offers_menu(call: CallbackQuery, _: Callable[[str], str]):
    from utils.keyboards import get_offers_menu_kb
    await call.message.edit_text(_("offers_menu.offers_title"), reply_markup=get_offers_menu_kb(_))
    await call.answer()

# Global cancel for FSM states, if any.
@router.callback_query(AdminCallback.filter(F.action == "cancel_broadcast"))
async def cancel_fsm_operation(call: CallbackQuery, state: FSMContext, _: Callable[[str], str]):
    current_state = await state.get_state()
    if current_state:
        from utils.keyboards import get_admin_main_menu_kb
        await state.clear()
        await call.message.answer(_("common.cancel"), reply_markup=get_admin_main_menu_kb(_))
        await call.answer(_("common.cancel"))
    else:
        await call.answer(_("common.no_active_operation"), show_alert=True)


def register_callbacks(dp: Router):
    # This function is used by bot.py to include this router.
    # No additional logic needed here, just the router itself.
    pass
