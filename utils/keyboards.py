# utils/keyboards.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from utils.callbacks import LanguageCallback, ChannelCallback, BoostOrderCallback, MainMenuCallback, WalletCallback, PromocodeCallback, AdminCallback, AdminReportCallback
from typing import List, Optional, Callable, Dict, Any
from database.models import Channel
from config.settings import settings # Import settings

def get_language_kb():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Русский 🇷🇺", callback_data=LanguageCallback(lang_code="ru").pack()),
        InlineKeyboardButton(text="English 🇬🇧", callback_data=LanguageCallback(lang_code="en").pack()),
        InlineKeyboardButton(text="中文 🇨🇳", callback_data=LanguageCallback(lang_code="zh").pack())
    )
    return builder.as_markup()

def get_main_menu_kb(_: Callable[[str], str]) -> ReplyKeyboardMarkup: # _ is the translation function
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text=_("main_menu.buttons.boosting")))
    builder.row(
        KeyboardButton(text=_("main_menu.buttons.my_account")),
        KeyboardButton(text=_("main_menu.buttons.wallet"))
    )
    builder.row(KeyboardButton(text=_("main_menu.buttons.offers")))
    return builder.as_markup(resize_keyboard=True)

def get_boosting_menu_kb(_: Callable[[str], str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=_("boosting_menu.active_orders"), callback_data=MainMenuCallback(action="active_boosts").pack()))
    builder.row(InlineKeyboardButton(text=_("boosting_menu.order_history"), callback_data=MainMenuCallback(action="boost_history").pack()))
    builder.row(InlineKeyboardButton(text=_("boosting_menu.order_new"), callback_data=MainMenuCallback(action="new_boost").pack()))
    builder.row(InlineKeyboardButton(text=_("boosting_menu.my_channels"), callback_data=MainMenuCallback(action="my_channels").pack()))
    builder.row(InlineKeyboardButton(text=_("common.back_to_main"), callback_data=MainMenuCallback(action="main_menu").pack()))
    return builder.as_markup()

def get_boost_type_kb(_: Callable[[str], str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=_("boosting_menu.normal_type"), callback_data=BoostOrderCallback(action="type_select", order_type="normal").pack()),
        InlineKeyboardButton(text=_("boosting_menu.turbo_type"), callback_data=BoostOrderCallback(action="type_select", order_type="turbo").pack())
    )
    builder.row(InlineKeyboardButton(text=_("common.back"), callback_data=MainMenuCallback(action="boosting").pack()))
    return builder.as_markup()

def get_channel_selection_kb(channels: List[Channel], _: Callable[[str], str]) -> Optional[InlineKeyboardMarkup]:
    builder = InlineKeyboardBuilder()
    if not channels:
        return None
    for channel in channels:
        builder.row(InlineKeyboardButton(
            text=f"{channel.title} (@{channel.username})" if channel.username else channel.title,
            callback_data=ChannelCallback(action="select", channel_id=channel.id).pack()
        ))
    builder.row(InlineKeyboardButton(text=_("common.back"), callback_data=MainMenuCallback(action="boosting").pack()))
    return builder.as_markup()

def get_channel_manage_kb(channel: Channel, _: Callable[[str], str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=_("my_channels.view_stats"), callback_data=ChannelCallback(action="stats", channel_id=channel.id).pack()))
    builder.row(InlineKeyboardButton(text=_("my_channels.select_donors"), callback_data=ChannelCallback(action="add_donor", channel_id=channel.id).pack()))
    builder.row(InlineKeyboardButton(text=_("my_channels.buy_slots"), callback_data=ChannelCallback(action="buy_slot", channel_id=channel.id).pack())) # If slots are channel-specific
    builder.row(InlineKeyboardButton(text=_("common.back"), callback_data=MainMenuCallback(action="my_channels").pack()))
    return builder.as_markup()


def get_order_confirmation_kb(_: Callable[[str], str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=_("boosting_menu.run_order"), callback_data=BoostOrderCallback(action="confirm").pack()),
        InlineKeyboardButton(text=_("boosting_menu.cancel_order"), callback_data=BoostOrderCallback(action="cancel").pack())
    )
    builder.row(InlineKeyboardButton(text=_("common.back"), callback_data=MainMenuCallback(action="boosting").pack()))
    return builder.as_markup()

def get_account_menu_kb(_: Callable[[str], str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=_("my_account_menu.promocode"), callback_data=MainMenuCallback(action="promocode").pack()))
    builder.row(InlineKeyboardButton(text=_("my_account_menu.invite_friends"), callback_data=MainMenuCallback(action="invite_friends").pack()))
    # New WebApp button for registration/data collection
    builder.row(InlineKeyboardButton(text=_("my_account_menu.update_info"), web_app=WebAppInfo(url=settings.WEBAPP_BASE_URL + settings.WEBAPP_FRONTEND_PATH))) # WebApp
    builder.row(InlineKeyboardButton(text=_("common.back_to_main"), callback_data=MainMenuCallback(action="main_menu").pack()))
    return builder.as_markup()

def get_wallet_menu_kb(_: Callable[[str], str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=_("wallet_menu.buy_credits"), callback_data=WalletCallback(action="buy").pack()))
    builder.row(InlineKeyboardButton(text=_("wallet_menu.earn_credits"), callback_data=WalletCallback(action="earn").pack()))
    builder.row(InlineKeyboardButton(text=_("common.back_to_main"), callback_data=MainMenuCallback(action="main_menu").pack()))
    return builder.as_markup()

def get_cryptomus_prices_kb(_: Callable[[str], str], prices: Dict[int, float]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for credits, usd in prices.items():
        builder.row(InlineKeyboardButton(text=f"{credits} Credits / {usd} USDT", callback_data=WalletCallback(action="select_amount", credits=credits, usd_amount=usd).pack()))
    builder.row(InlineKeyboardButton(text=_("common.back"), callback_data=MainMenuCallback(action="wallet").pack()))
    return builder.as_markup()

def get_payment_status_kb(_: Callable[[str], str], invoice_uuid: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=_("wallet_menu.payment_check_status"), callback_data=WalletCallback(action="check_payment", invoice_uuid=invoice_uuid).pack()))
    builder.row(InlineKeyboardButton(text=_("common.back"), callback_data=MainMenuCallback(action="wallet").pack()))
    return builder.as_markup()

def get_promocode_menu_kb(_: Callable[[str], str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=_("my_account_menu.enter_promocode"), callback_data=PromocodeCallback(action="input").pack()))
    builder.row(InlineKeyboardButton(text=_("common.back"), callback_data=MainMenuCallback(action="my_account").pack()))
    return builder.as_markup()

def get_offers_menu_kb(_: Callable[[str], str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=_("offers_menu.become_pro"), callback_data=MainMenuCallback(action="become_pro").pack()))
    builder.row(InlineKeyboardButton(text=_("offers_menu.franchise"), callback_data=MainMenuCallback(action="franchise").pack()))
    builder.row(InlineKeyboardButton(text=_("common.back_to_main"), callback_data=MainMenuCallback(action="main_menu").pack()))
    return builder.as_markup()

def get_admin_main_menu_kb(_: Callable[[str], str]) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text=_("admin_panel.add_accounts")), KeyboardButton(text=_("admin_panel.account_stats")))
    builder.row(KeyboardButton(text=_("admin_panel.reports")), KeyboardButton(text=_("admin_panel.broadcast")))
    builder.row(KeyboardButton(text=_("admin_panel.commands_list_btn"))) # Button to list commands
    return builder.as_markup(resize_keyboard=True)

def get_admin_broadcast_cancel_kb(_: Callable[[str], str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=_("common.cancel"), callback_data=AdminCallback(action="cancel_broadcast").pack()))
    return builder.as_markup()

def get_admin_reports_kb(_: Callable[[str], str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=_("admin_panel.reports_menu.financial"), callback_data=AdminReportCallback(action="financial").pack()))
    builder.row(InlineKeyboardButton(text=_("admin_panel.reports_menu.orders"), callback_data=AdminReportCallback(action="orders").pack()))
    builder.row(InlineKeyboardButton(text=_("admin_panel.reports_menu.topups"), callback_data=AdminReportCallback(action="topups").pack()))
    builder.row(InlineKeyboardButton(text=_("common.back"), callback_data=MainMenuCallback(action="admin_panel").pack()))
    return builder.as_markup()