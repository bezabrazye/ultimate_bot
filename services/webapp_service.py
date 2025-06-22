# services/webapp_service.py
from typing import Dict, Any, Optional
import hmac
import hashlib
from datetime import datetime
from urllib.parse import parse_qsl

from config.settings import settings
from database.repositories import UserRepository
from database.models import User
import logging

logger = logging.getLogger(__name__)

class WebAppService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def process_webapp_auth_data(self, init_data_raw: str, ip_address: str) -> bool:
        """
        Validates Telegram WebApp initData and updates user's IP and session fingerprint.
        Args:
            init_data_raw: The raw initData string received from Telegram WebApp.
            ip_address: The IP address of the client making the request to the webapp backend.
        Returns:
            True if data processed successfully, False otherwise.
        """
        if not self._validate_init_data(init_data_raw):
            logger.warning(f"Invalid initData from IP {ip_address}")
            return False

        parsed_data = dict(parse_qsl(init_data_raw))
        user_data_str = parsed_data.get('user')
        if not user_data_str:
            logger.warning(f"initData missing user info: {init_data_raw}")
            return False

        try:
            # Parse user data from initData string
            # It's a JSON string, so usually you'd parse it with json.loads
            # For simplicity, extract necessary fields from raw string.
            user_id_match = next(re.finditer(r'"id":(\d+)', user_data_str)).group(1)
            user_id = int(user_id_match)
            username_match = next(re.finditer(r'"username":"([^"]+)"', user_data_str)).group(1) if '"username":' in user_data_str else None
            first_name_match = next(re.finditer(r'"first_name":"([^"]+)"', user_data_str)).group(1) if '"first_name":' in user_data_str else None

            # Generate a session fingerprint. This is NOT a device serial number.
            # It's a unique hash for this specific WebApp session based on Telegram provided data.
            # Can include user.id, auth_date, query_id for better uniqueness.
            auth_date = parsed_data.get('auth_date', '')
            query_id = parsed_data.get('query_id', '')
            session_fingerprint = hashlib.sha256(f"{user_id}{auth_date}{query_id}{ip_address}".encode()).hexdigest()

        except (ValueError, AttributeError) as e:
            logger.error(f"Error parsing user data from initData: {user_data_str}, error: {e}", exc_info=True)
            return False

        user = await self.user_repo.get_user_by_id(user_id)
        if not user:
            # This should ideally not happen if UserMiddleware already created the user,
            # but good fallback to create minimal info or warn.
            user = User(
                id=user_id,
                username=username_match,
                first_name=first_name_match,
                ip_addresses=[ip_address],
                session_fingerprints=[session_fingerprint]
            )
            await self.user_repo.create_user(user)
            logger.info(f"Created new user {user_id} from WebApp auth.")
            return True

        # Update user's IP addresses and session fingerprints
        update_data = {}
        if ip_address not in user.ip_addresses:
            await self.user_repo.update({"_id": user_id}, {"$addToSet": {"ip_addresses": ip_address}})
            logger.info(f"Added new IP {ip_address} for user {user_id}")
        
        if session_fingerprint not in user.session_fingerprints:
            await self.user_repo.update({"_id": user_id}, {"$addToSet": {"session_fingerprints": session_fingerprint}})
            logger.info(f"Added new session fingerprint for user {user_id}")
        
        return True

    def _validate_init_data(self, init_data_raw: str) -> bool:
        """
        Validates the Telegram WebApp initData.
        This is a critical security step to prevent spoofing.
        Source: https://core.telegram.org/bots/webapps#checking-authorization
        """
        if not settings.WEBAPP_INITDATA_SECRET:
            logger.error("WEBAPP_INITDATA_SECRET is not set. initData validation skipped. This is INSECURE!")
            return True # Insecure, for dev only. DO NOT DO THIS IN PRODUCTION.

        parsed_data = dict(parse_qsl(init_data_raw))
        
        # 'hash' is the signature, remove it before sorting and hashing
        hash_to_check = parsed_data.pop('hash', None)
        if not hash_to_check:
            logger.warning("initData hash is missing.")
            return False

        data_check_string = "\n".join([f"{k}={v}" for k, v in sorted(parsed_data.items())])
        
        secret_key = hashlib.sha256(settings.BOT_TOKEN.encode()).digest() # Bot token is the base secret
        
        # Use HMAC-SHA256 initialized with the secret key, and update it with the data_check_string
        # The key for HMAC-SHA256 is HMAC_SHA256(secret_key, "WebAppData")
        # And then the hash of the data_check_string signed with that key
        data_check_hashed = hmac.new(secret_key, b"WebAppData", hashlib.sha256).digest()
        calculated_hash = hmac.new(data_check_hashed, data_check_string.encode(), hashlib.sha256).hexdigest()

        if calculated_hash == hash_to_check:
            # Check auth_date for freshness (e.g., within 24 hours) to prevent replay attacks
            auth_date_unix = int(parsed_data.get('auth_date', 0))
            auth_datetime = datetime.fromtimestamp(auth_date_unix)
            if datetime.now() - auth_datetime < timedelta(days=1):
                return True
            else:
                logger.warning(f"initData too old. Auth date: {auth_datetime}")
                return False
        else:
            logger.warning(f"initData hash mismatch. Calculated: {calculated_hash}, Received: {hash_to_check}")
            return False
            
import re # Add import for re
from datetime import timedelta