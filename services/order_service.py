# services/order_service.py
from datetime import datetime
from typing import Optional, List
from database.models import User, Channel, Order
from database.repositories import OrderRepository, UserRepository
import logging

logger = logging.getLogger(__name__)

class OrderService:
    def __init__(self, order_repo: OrderRepository, user_repo: UserRepository):
        self.order_repo = order_repo
        self.user_repo = user_repo

    async def create_boost_order(self, user: User, channel: Channel, order_type: str, requested_subscribers: int) -> Optional[Order]:
        cost_per_subscriber = 1 # Normal mode
        if order_type == "turbo":
            cost_per_subscriber = 2 # +100% cost

        total_cost = requested_subscribers * cost_per_subscriber

        if user.balance < total_cost:
            return None # Insufficient funds (handled outside)

        # Deduct balance first to avoid race conditions with order creation
        # Important: Pass the user object to deduct_user_balance so its in-memory balance updates
        if not await self.user_repo.increment_balance(user.id, -total_cost):
            logger.error(f"Failed to deduct balance for user {user.id} for order.")
            return None

        # Update user's in-memory object (balance)
        user.balance -= total_cost


        new_order = Order(
            user_id=user.id,
            channel_id=channel.id,
            order_type=order_type,
            requested_subscribers=requested_subscribers,
            cost_credits=total_cost,
            status="pending"
        )
        created_order = await self.order_repo.create_order(new_order)
        if created_order:
            logger.info(f"Order {created_order.id} created for user {user.id} on channel {channel.id}. Cost: {total_cost}")
            # Also update user's order history (list of order IDs)
            user_update_success = await self.user_repo.update({"_id": user.id}, {"$push": {"order_history_ids": created_order.id}})
            if not user_update_success:
                logger.warning(f"Failed to append order ID {created_order.id} to user {user.id}'s history.")
            return created_order
        else:
            # If order creation fails, try to refund user (important!)
            await self.user_repo.increment_balance(user.id, total_cost)
            # Rollback user's in-memory balance
            user.balance += total_cost
            logger.error(f"Failed to record order in DB for user {user.id}. Funds refunded.")
            return None

    async def get_active_orders(self, user_id: int) -> List[Order]:
        return await self.order_repo.get_user_orders(user_id, status_filter="running")

    async def get_order_history(self, user_id: int) -> List[Order]:
        return await self.order_repo.get_user_orders(user_id, status_filter="completed")
    
    # In a real system, you'd have methods here to interact with the actual boosting mechanism
    # e.g., send_order_to_booster_system(order_id), receive_booster_update(order_id, fulfilled, errors)
    # This bot's role is mostly UI and order management, the boosting itself is an external "engine".

2.19 services/payment_service.py
# services/payment_service.py
import httpx
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from database.models import User, Transaction
from database.repositories import UserRepository, TransactionRepository
from config.settings import settings
import logging
import hashlib
import uuid # For unique transaction ID

logger = logging.getLogger(__name__)

class PaymentService:
    def __init__(self, user_repo: UserRepository, transaction_repo: TransactionRepository):
        self.user_repo = user_repo
        self.transaction_repo = transaction_repo
        self.CRYPTOMUS_API_BASE_URL = "https://api.cryptomus.com/v1"
        self.HEADERS = {
            "Content-Type": "application/json",
            "merchant": settings.CRYPTOMUS_MERCHANT_ID,
            "sign": "" # This will be generated per request
        }
        self.PRICES = {
            100: 5.0,    # 100 credits = 5 USDT
            500: 20.0,   # 500 credits = 20 USDT
            1000: 35.0,  # 1000 credits = 35 USDT
            5000: 150.0, # 5000 credits = 150 USDT
            10000: 250.0 # 10000 credits = 250 USDT
        } # Credits: USD

    def _generate_signature(self, data: Dict[str, Any]) -> str:
        """
        Generates Cryptomus API signature.
        Requires data to be sorted by key alphabetically.
        """
        # Cryptomus expects string concatenation of sorted payload values + API key + secret
        # However, their new API (v2) uses HMAC SHA256. For MD5, it's typically just values.
        # Let's use the provided example MD5 generation, which is common for older APIs.
        stringified_data = ""
        for key in sorted(data.keys()):
            stringified_data += str(data[key])
        combined_string = stringified_data + settings.CRYPTOMUS_API_KEY
        return hashlib.md5(combined_string.encode('utf-8')).hexdigest()

    def get_price_options(self) -> Dict[int, float]:
        return self.PRICES

    async def create_cryptomus_invoice(self, user_id: int, credits_amount: int, usd_amount: float) -> Optional[tuple[Transaction, Dict]]:
        order_id = str(uuid.uuid4()) # Unique order ID for Cryptomus
        
        # Cryptomus requires amount as string
        payload = {
            "amount": str(usd_amount), 
            "currency": "USD",
            "order_id": order_id,
            "url_return": "https://t.me/your_bot_username", # Redirect URL after payment. CHANGE THIS!
            "url_callback": f"YOUR_PUBLIC_WEBHOOK_URL/cryptomus_webhook/{settings.CRYPTOMUS_WEBHOOK_SECRET}", # Crucial! CHANGE THIS!
            "lifetime": 900, # 15 minutes in seconds
            "is_payment_multiple": False,
            "to_currency": "USDT", # Suggests default payout currency (important for generated address type)
        }
        self.HEADERS["sign"] = self._generate_signature(payload)

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.CRYPTOMUS_API_BASE_URL}/payment/create",
                    json=payload,
                    headers=self.HEADERS
                )
                response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
                result = response.json()

                if result["state"] == 0: # Success
                    invoice_data = result["result"]
                    new_transaction = Transaction(
                        user_id=user_id,
                        amount_usd=usd_amount,
                        amount_credits=credits_amount,
                        crypto_currency=invoice_data["network"] if "network" in invoice_data else "UNKNOWN", # Initial currency of generated address
                        cryptomus_uuid=invoice_data["uuid"],
                        cryptomus_address=invoice_data.get("address", "N/A"), # Address might not be immediately available
                        status="pending",
                        expires_at=datetime.now() + timedelta(seconds=invoice_data["lifetime"]) # Use actual lifetime from API (if provided, else default to 15 min)
                    )
                    created_transaction = await self.transaction_repo.create_transaction(new_transaction)
                    if created_transaction:
                        logger.info(f"Cryptomus invoice created for user {user_id}. Invoice UUID: {invoice_data['uuid']}")
                        return created_transaction, invoice_data
                    else:
                        logger.error(f"Failed to save transaction to DB for user {user_id}.")
                        return None, None
                else:
                    logger.error(f"Cryptomus API error creating invoice: {result.get('message')}. Errors: {result.get('errors')}")
                    return None, None
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error during Cryptomus invoice creation: {e.response.status_code} - {e.response.text}", exc_info=True)
            return None, None
        except Exception as e:
            logger.error(f"Error during Cryptomus invoice creation for user {user_id}: {e}", exc_info=True)
            return None, None

    async def check_cryptomus_payment_status(self, invoice_uuid: str) -> Optional[Transaction]:
        payload = {"uuid": invoice_uuid}
        self.HEADERS["sign"] = self._generate_signature(payload)

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(
                    f"{self.CRYPTOMUS_API_BASE_URL}/payment/info",
                    json=payload,
                    headers=self.HEADERS
                )
                response.raise_for_status()
                result = response.json()

                if result["state"] == 0:
                    payment_info = result["result"]
                    transaction = await self.transaction_repo.get_transaction_by_cryptomus_uuid(invoice_uuid)
                    if transaction:
                        cryptomus_status = payment_info["status"] # e.g., "paid", "confirmed", "fail", "check", "stillWaiting"
                        
                        # Map Cryptomus status to our internal status
                        if cryptomus_status == "paid" or cryptomus_status == "paid_over" or cryptomus_status == "confirmed":
                            internal_status = "completed"
                            if transaction.status == "pending": # Only process if not already processed
                                await self._process_successful_payment(transaction)
                        elif cryptomus_status in ["fail", "expired", "cancel"]:
                            internal_status = "failed"
                        else: # "stillWaiting", "check", etc.
                            internal_status = "pending"

                        await self.transaction_repo.update_transaction(
                            transaction.id,
                            {
                                "status": internal_status,
                                "cryptomus_tx_id": payment_info.get("txid"),
                                "crypto_currency": payment_info.get("network", transaction.crypto_currency),
                                "processed_at": datetime.now() if internal_status == "completed" else None # Update time only on completion
                            }
                        )
                        # Re-fetch the updated transaction for consistency
                        return await self.transaction_repo.get_transaction_by_id(transaction.id)
                    else:
                        logger.warning(f"Transaction not found in DB for Cryptomus UUID: {invoice_uuid}.")
                        return None
                else:
                    logger.warning(f"Cryptomus API error checking status for {invoice_uuid}: {result.get('message')}")
                    return None
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error checking Cryptomus payment status for {invoice_uuid}: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Error checking Cryptomus payment status for {invoice_uuid}: {e}", exc_info=True)
            return None

    # This method should be called by Cryptomus webhook asynchronously
    async def process_cryptomus_webhook(self, data: Dict[str, Any], signature_header: str) -> bool:
        """
        Processes an incoming Cryptomus webhook.
        This function would typically be exposed via a web server (e.g., FastAPI, aiohttp).
        """
        # 1. Verify a signature
        # Cryptomus webhook signature is typically HMAC-SHA256 of payload + secret.
        # The provided Cryptomus example uses MD5 of sorted concatenation + API_KEY for *API calls*,
        # but webhooks often use a different signature method.
        # ***ALWAYS REFER TO THE LATEST CRYPTOMUS WEBHOOK DOCUMENTATION FOR SIGNATURE VERIFICATION***
        # This is a placeholder. A proper check would compute expected signature and compare.
        # Example (conceptual, depends on Cryptomus exact webhook signing):
        # expected_sign = hashlib.sha256((str(data).encode() + settings.CRYPTOMUS_WEBHOOK_SECRET.encode())).hexdigest()
        # if expected_sign != signature_header:
        #     logger.warning("Cryptomus webhook signature mismatch.")
        #     return False

        # 2. Extract relevant info
        invoice_uuid = data.get("uuid")
        payment_status = data.get("status")
        amount = float(data.get("amount"))
        actual_currency = data.get("currency")
        tx_id = data.get("txid") # Blockchain transaction ID
        
        if not invoice_uuid or not payment_status:
            logger.warning("Cryptomus webhook missing essential data.")
            return False

        transaction = await self.transaction_repo.get_transaction_by_cryptomus_uuid(invoice_uuid)
        if not transaction:
            logger.warning(f"Cryptomus webhook received for unknown invoice: {invoice_uuid}. Status: {payment_status}")
            return False

        if payment_status == "paid" or payment_status == "paid_over" or payment_status == "confirmed":
            if transaction.status == "pending": # Only process if not already processed
                # Ensure amount matches expected, prevent tampering
                if abs(transaction.amount_usd - amount) > 0.01: # Small float tolerance
                    logger.error(f"Amount mismatch for transaction {transaction.id}. Expected {transaction.amount_usd}, got {amount}. Marking transaction as fraudulent.")
                    await self.transaction_repo.update_transaction(
                        transaction.id,
                        {"status": "failed", "cryptomus_tx_id": tx_id, "processed_at": datetime.now(), "error_notes": "Amount mismatch"}
                    )
                    return False # Indicate failure due to mismatch

                success = await self._process_successful_payment(transaction)
                if success:
                    await self.transaction_repo.update_transaction(
                        transaction.id,
                        {"status": "completed", "cryptomus_tx_id": tx_id, "crypto_currency": actual_currency, "processed_at": datetime.now()}
                    )
                    logger.info(f"Transaction {transaction.id} ({invoice_uuid}) completed via webhook. {transaction.amount_credits} credits added to user {transaction.user_id}.")
                    return True
                else:
                    await self.transaction_repo.update_transaction(
                        transaction.id,
                        {"status": "failed", "cryptomus_tx_id": tx_id, "processed_at": datetime.now(), "error_notes": "Failed to credit user balance"}
                    )
                    logger.error(f"Failed to credit balance for user {transaction.user_id} from transaction {transaction.id}.")
                    return False
            else:
                logger.info(f"Cryptomus webhook for invoice {invoice_uuid} already processed. Status: {transaction.status}")
                return True # Already processed, consider it success for webhook

        elif payment_status == "fail" or payment_status == "expired" or payment_status == "cancel":
            await self.transaction_repo.update_transaction(
                transaction.id,
                {"status": "failed", "processed_at": datetime.now()}
            )
            logger.warning(f"Cryptomus payment failed/expired/cancelled for invoice {invoice_uuid}. Status: {payment_status}")
            return True # Successfully handled status update for failed transactions
        else:
            logger.warning(f"Cryptomus webhook unknown payment status: {payment_status} for invoice {invoice_uuid}.")
            return False # Indicate this webhook wasn't handled fully


    async def _process_successful_payment(self, transaction: Transaction) -> bool:
        """Helper to process adding credits and referral bonuses."""
        user = await self.user_repo.get_user_by_id(transaction.user_id)
        if not user:
            logger.error(f"User not found for transaction {transaction.id}. Cannot credit balance.")
            return False
        
        # Add credits to user's balance
        success = await self.user_repo.increment_balance(user.id, transaction.amount_credits)
        if not success:
            return False
        
        # Handle referral bonuses
        if user.referrer_id:
            referrer = await self.user_repo.get_user_by_id(user.referrer_id)
            if referrer:
                # Increment count of referred users who paid
                await self.user_repo.increment({"_id": referrer.id}, "referred_users_paid_count")
                # Reload referrer to get updated count for calculations
                referrer_updated = await self.user_repo.get_user_by_id(referrer.id)

                # Award for 1 user making first payment of >= 10$
                if transaction.amount_usd >= 10 and referrer_updated.referred_users_paid_count == 1: # Only for the first actual payment
                    await self.user_repo.increment_balance(referrer.id, 100)
                    await self.user_repo.increment({"_id": referrer.id}, "earned_referral_credits", 100)
                    logger.info(f"Awarded 100 referral credits to {referrer.id} for {user.id}'s first payment >=$10.")
                
                # Award 150 credits for 5 users making >= 5$
                # This check ensures it's exactly the 5th user that triggers the bonus
                if referrer_updated.referred_users_paid_count == 5:
                    await self.user_repo.increment_balance(referrer.id, 150)
                    await self.user_repo.increment({"_id": referrer.id}, "earned_referral_credits", 150)
                    logger.info(f"Awarded 150 referral credits to {referrer.id} for reaching 5 referred users paid.")

        return True