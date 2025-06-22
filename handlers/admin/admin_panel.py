# handlers/admin/admin_panel.py
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from typing import Callable, Optional
from datetime import datetime, date

from database.models import User
from services.admin_service import AdminService
from services.mailing_service import MailingService
from utils.keyboards import get_admin_main_menu_kb, get_admin_broadcast_cancel_kb, get_admin_reports_kb, get_main_menu_kb
from utils.filters import AdminFilter
from utils.states import Form
from utils.callbacks import AdminCallback, AdminReportCallback
from utils.misc import format_datetime

router = Router()
router.message.filter(AdminFilter()) # Apply admin filter to all messages in this router
router.callback_query.filter(AdminFilter()) # Apply admin filter to all callbacks in this router


@router.message(F.text == "/admin")
async def cmd_admin_panel(message: Message, state: FSMContext, _: Callable[[str], str]):
    await state.clear()
    await message.answer(_("admin_panel.access_granted"), reply_markup=get_admin_main_menu_kb(_))

@router.message(F.text == "/cmds")
async def cmd_admin_commands(message: Message, _: Callable[[str], str]):
    await message.answer(_("admin_panel.commands_list"))

@router.message(F.text.startswith("/ban "))
async def cmd_ban_user(message: Message, admin_service: AdminService, _: Callable[[str], str]):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Usage: `/ban [id|@username]`")
        return
    identifier = args[1].strip()
    
    user = await admin_service.ban_user(identifier)
    if user:
        await message.answer(_("admin_panel.user_banned").format(id=user.id, username=user.username or "N/A"))
    else:
        await message.answer(_("admin_panel.user_not_found"))

@router.message(F.text.startswith("/unban "))
async def cmd_unban_user(message: Message, admin_service: AdminService, _: Callable[[str], str]):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Usage: `/unban [id|@username]`")
        return
    identifier = args[1].strip()
    
    user = await admin_service.unban_user(identifier)
    if user:
        await message.answer(_("admin_panel.user_unbanned").format(id=user.id, username=user.username or "N/A"))
    else:
        await message.answer(_("admin_panel.user_not_found"))

@router.message(F.text.startswith("/check "))
async def cmd_check_user(message: Message, admin_service: AdminService, _: Callable[[str], str]):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Usage: `/check [id|@username]`")
        return
    identifier = args[1].strip()

    user = await admin_service.get_user_info(identifier)
    if user:
        pro_status_text = _("my_account_menu.pro_status_inactive")
        if user.is_pro:
            pro_status_text = _("my_account_menu.pro_status_active")
            if user.pro_expires_at:
                pro_status_text += _("my_account_menu.pro_expires").format(date=user.pro_expires_at.strftime("%Y-%m-%d"))

        user_info_msg = _("admin_panel.user_info_msg").format(
                id=user.id,
                username=user.username or "N/A",
                first_name=user.first_name or "",
                last_name=user.last_name or "",
                balance=user.balance,
                num_channels=len(user.channels),
                max_slots=user.max_channels_slots,
                is_admin=user.is_admin,
                is_pro=user.is_pro,
                warnings=user.warnings,
                is_banned=user.is_banned
            )
        await message.answer(user_info_msg)
    else:
        await message.answer(_("admin_panel.user_not_found"))

@router.message(F.text.startswith("/set_balance "))
async def cmd_set_balance(message: Message, admin_service: AdminService, _: Callable[[str], str]):
    args = message.text.split()
    if len(args) < 3:
        await message.answer("Usage: `/set_balance [user_id] [amount]`")
        return
    
    try:
        user_id = int(args[1])
        amount = int(args[2])
    except ValueError:
        await message.answer("Invalid user ID or amount.")
        return

    user = await admin_service.set_user_balance(user_id, amount)
    if user:
        await message.answer(_("admin_panel.balance_updated").format(id=user.id, balance=user.balance))
    else:
        await message.answer(_("admin_panel.user_not_found"))

@router.message(F.text.startswith("/set_slots "))
async def cmd_set_slots(message: Message, admin_service: AdminService, _: Callable[[str], str]):
    args = message.text.split()
    if len(args) < 3:
        await message.answer("Usage: `/set_slots [user_id] [amount]`")
        return
    
    try:
        user_id = int(args[1])
        amount = int(args[2])
    except ValueError:
        await message.answer("Invalid user ID or amount.")
        return

    user = await admin_service.change_user_slots(user_id, amount)
    if user:
        await message.answer(_("admin_panel.slots_updated").format(id=user.id, slots=user.max_channels_slots))
    else:
        await message.answer(_("admin_panel.user_not_found"))


@router.message(F.text == "/promo")
async def cmd_promo_list(message: Message, admin_service: AdminService, _: Callable[[str], str]):
    promos = await admin_service.get_all_promo_codes()
    if not promos:
        await message.answer("No promo codes found.")
        return
    
    response_text = "<b>Promo Codes:</b>\n"
    for promo in promos:
        expires_at_str = promo.expires_at.strftime("%Y-%m-%d") if promo.expires_at else "N/A"
        response_text += (
            f"<b>{promo.name}</b>: {promo.credits} credits\n"
            f"  Activations: {promo.activations_used}/{promo.max_activations or '∞'}\n"
            f"  Expires: {expires_at_str}\n"
            f"  Active: {promo.is_active}\n"
            f"  One per IP/Serial: {promo.one_per_ip_serial}\n\n"
        )
    await message.answer(response_text, parse_mode='HTML')


@router.message(F.text.startswith("/add_promo "))
async def cmd_add_promo(message: Message, admin_service: AdminService, _: Callable[[str], str]):
    # /add_promo NAME CREDITS ACTIVATIONS [YYYY-MM-DD] [one_per_ip_serial:F|T]
    args = message.text.split()
    if len(args) < 4:
        await message.answer("Usage: `/add_promo NAME CREDITS ACTIVATIONS [YYYY-MM-DD] [true/false]`")
        return
    
    name = args[1]
    try:
        credits = int(args[2])
        max_activations = int(args[3]) if args[3].isdigit() else None
    except ValueError:
        await message.answer("Credits and activations must be numbers.")
        return

    expires_at_str = args[4] if len(args) > 4 else None
    one_per_ip_serial_str = args[5] if len(args) > 5 else "false"

    promo = await admin_service.add_promo_code(name, credits, max_activations, expires_at_str, one_per_ip_serial_str)
    if promo:
        await message.answer(_("admin_panel.promo_added").format(name=promo.name))
    else:
        await message.answer(_("admin_panel.promo_exists").format(name=name)) # Or invalid date

@router.message(F.text.startswith("/del_promo "))
async def cmd_del_promo(message: Message, admin_service: AdminService, _: Callable[[str], str]):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Usage: `/del_promo NAME`")
        return
    name = args[1].strip()

    if await admin_service.delete_promo_code(name):
        await message.answer(_("admin_panel.promo_deleted").format(name=name))
    else:
        await message.answer(_("admin_panel.promo_not_found").format(name=name))


@router.message(F.text == "/broadcast")
async def cmd_broadcast_start(message: Message, state: FSMContext, _: Callable[[str], str]):
    await message.answer(_("admin_panel.broadcast_prompt"), reply_markup=get_admin_broadcast_cancel_kb(_))
    await state.set_state(Form.admin_broadcast)

@router.message(Form.admin_broadcast)
async def cmd_broadcast_message(message: Message, state: FSMContext, mailing_service: MailingService, _: Callable[[str], str]):
    sent_count, total_count = await mailing_service.send_broadcast(message.html_text) # Use html_text for formatting
    await message.answer(_("admin_panel.broadcast_success").format(sent=sent_count, total=total_count), reply_markup=get_admin_main_menu_kb(_))
    await state.clear()

@router.callback_query(AdminCallback.filter(F.action == "cancel_broadcast"), Form.admin_broadcast)
async def cmd_broadcast_cancel_callback(call: CallbackQuery, state: FSMContext, _: Callable[[str], str]):
    await state.clear()
    await call.message.edit_text(_("admin_panel.broadcast_cancelled"), reply_markup=get_admin_main_menu_kb(_))
    await call.answer()


@router.message(F.text == "/account_stats")
async def cmd_account_stats(message: Message, admin_service: AdminService, _: Callable[[str], str]):
    stats = await admin_service.get_booster_accounts_stats()
    stats_text = _("admin_panel.account_stats").format(
        active_count=stats["active_count"],
        idle_count=stats["idle_count"],
        banned_count=stats["banned_count"],
        avg_speed=stats["average_daily_subs_per_account"]
    )
    await message.answer(stats_text)

@router.message(F.text == "/reports")
async def cmd_reports_menu(message: Message, _: Callable[[str], str]):
    await message.answer(_("admin_panel.reports_menu_title"), reply_markup=get_admin_reports_kb(_)) # Need reports_menu_title in locale

@router.callback_query(AdminReportCallback.filter(F.action == "financial"))
async def show_financial_report(call: CallbackQuery, admin_service: AdminService, _: Callable[[str], str]):
    report = await admin_service.get_financial_report()
    report_text = _("admin_panel.reports_menu.financial_report_msg").format(
        total_revenue_usd=report["total_revenue_usd"],
        total_credits_sold=report["total_credits_sold"],
        completed_transactions=report["completed_transactions"],
        average_check_usd=report["average_check_usd"]
    )
    await call.message.edit_text(report_text, reply_markup=get_admin_reports_kb(_))
    await call.answer()

@router.callback_query(AdminReportCallback.filter(F.action == "orders"))
async def show_orders_report(call: CallbackQuery, admin_service: AdminService, _: Callable[[str], str]):
    orders = await admin_service.get_orders_report()
    orders_list_str = "\n".join([f"ID: {o.id} | User: {o.user_id} | Channel: {o.channel_id} | Status: {o.status} | Subs: {o.fulfilled_subscribers}/{o.requested_subscribers}" for o in orders[:10]]) # Show first 10
    report_text = _("admin_panel.reports_menu.orders_report_msg").format(orders_list=orders_list_str if orders_list_str else "No orders.")
    await call.message.edit_text(report_text, reply_markup=get_admin_reports_kb(_))
    await call.answer()

@router.callback_query(AdminReportCallback.filter(F.action == "topups"))
async def show_topups_report(call: CallbackQuery, admin_service: AdminService, _: Callable[[str], str]):
    topups = await admin_service.get_top_ups_report()
    topups_list_str = "\n".join([f"ID: {t.id} | User: {t.user_id} | Amount: {t.amount_usd} ({t.amount_credits} cr) | Status: {t.status}" for t in topups[:10]]) # Show first 10
    report_text = _("admin_panel.reports_menu.topups_report_msg").format(topups_list=topups_list_str if topups_list_str else "No top-ups.")
    await call.message.edit_text(report_text, reply_markup=get_admin_reports_kb(_))
    await call.answer()
