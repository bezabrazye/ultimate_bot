# handlers/private/wallet.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from typing import Callable
from datetime import datetime

from database.models import User, Transaction
from services.payment_service import PaymentService
from utils.keyboards import get_wallet_menu_kb, get_cryptomus_prices_kb, get_payment_status_kb
from utils.callbacks import MainMenuCallback, WalletCallback
import logging

logger = logging.getLogger(__name__)

router = Router()

@router.callback_query(WalletCallback.filter(F.action == "buy"))
async def buy_credits_menu(call: CallbackQuery, payment_service: PaymentService, _: Callable[[str], str]):
    prices = payment_service.get_price_options()
    await call.message.edit_text(_("wallet_menu.select_amount_to_buy"), reply_markup=get_cryptomus_prices_kb(_, prices))
    await call.answer()

@router.callback_query(WalletCallback.filter(F.action == "select_amount"))
async def process_selected_amount(call: CallbackQuery, callback_data: WalletCallback, user: User, payment_service: PaymentService, _: Callable[[str], str]):
    credits = callback_data.credits
    usd_amount = callback_data.usd_amount
    
    if credits is None or usd_amount is None:
        await call.message.answer(_("error.default"), reply_markup=get_wallet_menu_kb(_))
        await call.answer(_("error.default"), show_alert=True)
        return

    # Check minimum amount (e.g., 100 credits = 5 USD)
    min_credits_amount = 100
    if credits < min_credits_amount:
         await call.message.answer(_("wallet_menu.payment_info_min_amount").format(min_usd=payment_service.PRICES.get(min_credits_amount, 0)), reply_markup=get_wallet_menu_kb(_))
         await call.answer(_("wallet_menu.payment_info_min_amount_alert"), show_alert=True)
         return

    transaction, invoice_data = await payment_service.create_cryptomus_invoice(user.id, credits, usd_amount)

    if transaction and invoice_data:
        payment_address = invoice_data.get("address")
        payment_network = invoice_data.get("network")
        checkout_url_general = invoice_data.get("url") # Cryptomus often provides a single checkout URL

        if not payment_address or not payment_network:
            # Fallback or indicate problem if crypto details not immediately available
            await call.message.edit_text(_("wallet_menu.payment_address_not_available"), reply_markup=get_wallet_menu_kb(_))
            await call.answer(_("wallet_menu.payment_address_not_available"), show_alert=True)
            return

        payment_info_text = _("wallet_menu.payment_info").format(
            amount=usd_amount,
            credits=credits,
            uuid=invoice_data["uuid"],
            address=payment_address,
            currency=payment_network,
            expires_at=transaction.expires_at.strftime("%Y-%m-%d %H:%M:%S"),
            min_usd=payment_service.PRICES.get(min_credits_amount, 0)
        )
        await call.message.edit_text(payment_info_text, parse_mode='HTML', reply_markup=get_payment_status_kb(_, transaction.cryptomus_uuid))
        # Log the checkout URL for debugging if needed, or provide it as a separate button for user
        if checkout_url_general:
            logger.info(f"Cryptomus Checkout URL for {user.id}: {checkout_url_general}")
            # You might add a button here for the general checkout URL

    else:
        await call.message.edit_text(_("error.default"), reply_markup=get_wallet_menu_kb(_))
    
    await call.answer()

@router.callback_query(WalletCallback.filter(F.action == "check_payment"))
async def check_payment_status_callback(call: CallbackQuery, callback_data: WalletCallback, user: User, payment_service: PaymentService, _: Callable[[str], str]):
    invoice_uuid = callback_data.invoice_uuid
    if not invoice_uuid:
        await call.message.answer(_("error.default"), reply_markup=get_wallet_menu_kb(_))
        await call.answer()
        return

    await call.answer(_("wallet_menu.payment_check_status"), show_alert=False) # Show temporary alert

    updated_transaction = await payment_service.check_cryptomus_payment_status(invoice_uuid)

    if updated_transaction:
        if updated_transaction.status == "completed":
            await call.message.answer(_("wallet_menu.payment_completed"), reply_markup=get_wallet_menu_kb(_))
        elif updated_transaction.status == "pending":
            await call.message.answer(_("wallet_menu.payment_pending"), reply_markup=get_payment_status_kb(_, invoice_uuid))
        else: # failed, expired
            await call.message.answer(_("wallet_menu.payment_failed"), reply_markup=get_wallet_menu_kb(_))
    else:
        await call.message.answer(_("error.default"), reply_markup=get_wallet_menu_kb(_))

@router.callback_query(WalletCallback.filter(F.action == "earn"))
async def earn_credits_menu(call: CallbackQuery, _: Callable[[str], str]):
    await call.message.edit_text(_("wallet_menu.earn_credits_ad_info"), reply_markup=get_wallet_menu_kb(_))
    await call.answer()