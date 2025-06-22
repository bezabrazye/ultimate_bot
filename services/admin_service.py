# services/admin_service.py
from typing import Optional, List, Dict
from datetime import datetime, date
from database.repositories import UserRepository, OrderRepository, TransactionRepository, PromoCodeRepository, BoosterAccountRepository
from database.models import User, PromoCode, Order, Transaction, BoosterAccount
import logging

logger = logging.getLogger(__name__)

class AdminService:
    def __init__(self,
                 user_repo: UserRepository,
                 order_repo: OrderRepository,
                 transaction_repo: TransactionRepository,
                 promo_repo: PromoCodeRepository,
                 booster_account_repo: BoosterAccountRepository):
        self.user_repo = user_repo
        self.order_repo = order_repo
        self.transaction_repo = transaction_repo
        self.promo_repo = promo_repo
        self.booster_account_repo = booster_account_repo

    async def find_user_by_identifier(self, identifier: str) -> Optional[User]:
        if identifier.isdigit():
            return await self.user_repo.get_user_by_id(int(identifier))
        elif identifier.startswith('@'):
            return await self.user_repo.get_one({"username": identifier[1:]})
        return None

    async def ban_user(self, identifier: str) -> Optional[User]:
        user = await self.find_user_by_identifier(identifier)
        if not user:
            return None

        modified_count = await self.user_repo.update_user(user.id, {"is_banned": True})
        if modified_count > 0:
            user.is_banned = True # Update local object
            logger.info(f"User {user.id} (@{user.username}) has been banned by admin.")
            return user
        return None

    async def unban_user(self, identifier: str) -> Optional[User]:
        user = await self.find_user_by_identifier(identifier)
        if not user:
            return None

        modified_count = await self.user_repo.update_user(user.id, {"is_banned": False, "warnings": 0})
        if modified_count > 0:
            user.is_banned = False
            user.warnings = 0
            logger.info(f"User {user.id} (@{user.username}) has been unbanned by admin.")
            return user
        return None

    async def get_user_info(self, identifier: str) -> Optional[User]:
        return await self.find_user_by_identifier(identifier)

    async def set_user_balance(self, user_id: int, amount: int) -> Optional[User]:
        user = await self.user_repo.get_user_by_id(user_id)
        if not user:
            return None
        modified_count = await self.user_repo.update_user(user_id, {"balance": amount})
        if modified_count > 0:
            user.balance = amount
            logger.info(f"Admin set balance for user {user_id} to {amount}.")
            return user
        return None
    
    async def change_user_slots(self, user_id: int, new_slots: int) -> Optional[User]:
        user = await self.user_repo.get_user_by_id(user_id)
        if not user:
            return None
        modified_count = await self.user_repo.update_user(user.id, {"max_channels_slots": new_slots})
        if modified_count > 0:
            user.max_channels_slots = new_slots
            logger.info(f"Admin changed slots for user {user_id} to {new_slots}.")
            return user
        return None

    async def add_promo_code(self, name: str, credits: int, max_activations: Optional[int], expires_at_str: Optional[str], one_per_ip_serial_str: str) -> Optional[PromoCode]:
        expires_at = None
        if expires_at_str:
            try:
                expires_at = datetime.strptime(expires_at_str, "%Y-%m-%d")
            except ValueError:
                return None # Invalid date format

        one_per_ip_serial = one_per_ip_serial_str.lower() in ['true', 't', '1']

        existing_promo = await self.promo_repo.get_promo_code_by_name(name)
        if existing_promo:
            logger.warning(f"Attempted to add existing promo code: {name}")
            return None # Promo code with this name already exists

        new_promo = PromoCode(
            name=name.upper(),
            credits=credits,
            max_activations=max_activations,
            expires_at=expires_at,
            one_per_ip_serial=one_per_ip_serial
        )
        created_promo = await self.promo_repo.create_promo_code(new_promo)
        if created_promo:
            logger.info(f"Admin added new promo code: {name.upper()}")
        return created_promo

    async def delete_promo_code(self, name: str) -> bool:
        # We deactivate promo codes, not delete them
        modified_count = await self.promo_repo.update_promo_code(name, {"is_active": False})
        if modified_count > 0:
            logger.info(f"Admin deactivated promo code: {name.upper()}")
            return True
        return False
    
    async def get_all_promo_codes(self) -> List[PromoCode]:
        return await self.promo_repo.get_many({}, limit=0)

    async def get_financial_report(self) -> dict:
        total_revenue_usd = 0.0
        total_credits_sold = 0
        transactions = await self.transaction_repo.get_many({"status": "completed"}) # Only completed ones
        
        for tx in transactions:
            total_revenue_usd += tx.amount_usd
            total_credits_sold += tx.amount_credits

        average_check = total_revenue_usd / len(transactions) if transactions else 0

        return {
            "total_revenue_usd": total_revenue_usd,
            "total_credits_sold": total_credits_sold,
            "completed_transactions": len(transactions),
            "average_check_usd": average_check
        }

    async def get_orders_report(self) -> List[Order]:
        return await self.order_repo.get_many({}, limit=0) # Return all orders

    async def get_top_ups_report(self) -> List[Transaction]:
        return await self.transaction_repo.get_many({}, limit=0) # Return all transactions

    async def add_booster_account(self, phone_number: str, session_file_path: str, proxy: Optional[str] = None) -> Optional[BoosterAccount]:
        account_data = BoosterAccount(
            phone_number=phone_number,
            session_file_path=session_file_path,
            proxies=proxy,
            status="active" # Assuming active upon addition
        )
        return await self.booster_account_repo.create_booster_account(account_data)

    async def get_booster_accounts_stats(self) -> dict:
        active_accounts = await self.booster_account_repo.get_many({"status": "active"}, limit=0)
        idle_accounts = await self.booster_account_repo.get_many({"status": "idle"}, limit=0)
        banned_accounts = await self.booster_account_repo.get_many({"status": "banned"}, limit=0)
        
        # Calculate average speed (conceptual, needs real data from boosting activity)
        # For now, if current_daily_subs is logged, we can use it.
        total_speed = sum(a.current_daily_subs for a in active_accounts)
        avg_speed = total_speed / len(active_accounts) if active_accounts else 0

        return {
            "active_count": len(active_accounts),
            "idle_count": len(idle_accounts),
            "banned_count": len(banned_accounts),
            "total_accounts": len(active_accounts) + len(idle_accounts) + len(banned_accounts),
            "average_daily_subs_per_account": avg_speed,
            "optimization_suggestions": "Monitor daily performance, replace banned accounts, optimize proxy usage." # Placeholder
        }
