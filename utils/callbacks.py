# utils/callbacks.py
from aiogram.filters.callback_data import CallbackData
from typing import Optional

class LanguageCallback(CallbackData, prefix="set_lang"):
    lang_code: str

class MainMenuCallback(CallbackData, prefix="main_menu"):
    action: str # "boosting", "my_account", "wallet", "offers", "main_menu", etc.

class ChannelCallback(CallbackData, prefix="channel"):
    action: str # "select", "stats", "add_donor", "buy_slot"
    channel_id: int

class BoostOrderCallback(CallbackData, prefix="boost_order"):
    action: str # "type_select", "channel_select", "confirm", "cancel"
    order_type: Optional[str] = None # "normal", "turbo"
    channel_id: Optional[int] = None

class WalletCallback(CallbackData, prefix="wallet"):
    action: str # "buy", "earn", "select_amount", "check_payment", "cancel_payment"
    credits: Optional[int] = None # Amount of credits
    usd_amount: Optional[float] = None # Amount in USD
    invoice_uuid: Optional[str] = None # Cryptomus invoice UUID

class PromocodeCallback(CallbackData, prefix="promocode"):
    action: str # "input", "apply"

class AdminCallback(CallbackData, prefix="admin_cmd"):
    action: str # e.g., "ban", "check", "set_balance", "set_slots", "add_promo", "del_promo", "broadcast"
    user_id: Optional[int] = None # For specific user actions
    promo_name: Optional[str] = None # For promo actions

class AdminReportCallback(CallbackData, prefix="admin_report"):
    action: str # "financial", "orders", "topups"
