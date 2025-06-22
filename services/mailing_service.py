# services/mailing_service.py
import asyncio
from datetime import datetime, time, timedelta
import random
from typing import List, Dict, Any
from aiogram import Bot
from database.repositories import UserRepository
from utils.misc import safe_send_message # Custom helper for robust sending
import logging

logger = logging.getLogger(__name__)

# Mailing templates (simplified, could be loaded from external files/DB)
MAILING_TEMPLATES = {
    "motivation": [
        "🚀 Go for new heights with our promotion bot! Your channel deserves to shine.",
        "💡 Don't just dream of growth, achieve it! Our tools are here to help."
    ],
    "deadline": [
        "⏳ Last chance! Special offer expires today. Don't miss out!",
        "⏰ Time is running out for our exclusive PRO plan discount!"
    ],
    "comparison": [
        "📈 See how your channel can outperform competitors with smart promotion.",
        "📊 Our users achieve X times faster growth than average. Join them now!"
    ],
    "promo_offer": [
        "🎁 New promo code 'SUPERBOOST' for extra credits! Limited time.",
        "✨ Get 20% more credits on your next top-up. Use code 'SPRING24'."
    ],
    "social_pressure": [ # Renamed from social_pressure for consistency
        "🌟 Over 10,000 channels have already boosted their audience with us!",
        "👥 Join our growing community of successful channel owners."
    ],
    "custom_behavior": [ # For personalized messages based on user behavior
        "👋 Hello {user_name}! Your channel '{channel_name}' has great potential. Want to unlock it?",
        "📉 Noticed a dip in your channel's activity? Let's fix it! Check our new features."
    ]
}

class MailingService:
    def __init__(self, bot: Bot, user_repo: UserRepository):
        self.bot = bot
        self.user_repo = user_repo

    async def send_random_mailing(self, template_type: str):
        """Sends a random message from a given template type to all active users."""
        if template_type not in MAILING_TEMPLATES:
            logger.warning(f"Unknown mailing template type: {template_type}")
            return

        template_messages = MAILING_TEMPLATES[template_type]
        if not template_messages:
            logger.warning(f"No messages found for template type: {template_type}")
            return

        message_text = random.choice(template_messages)
        users = await self.user_repo.get_many({"is_banned": False}, limit=0) 

        sent_count = 0
        total_users = len(users)
        logger.info(f"Starting mailing '{template_type}' to {total_users} users.")

        for user_item in users:
            # Personalize message if placeholders are present
            first_channel_name = user_item.channels[0].title if user_item.channels else "your channel"
            final_message = message_text.format(
                user_name=user_item.first_name or user_item.username or "there",
                channel_name=first_channel_name
            )

            try:
                await safe_send_message(self.bot, user_item.id, final_message)
                sent_count += 1
                await asyncio.sleep(0.05) # Small delay to avoid hitting Telegram API limits
            except Exception as e:
                # safe_send_message will handle TelegramBadRequest, other exceptions re-raised or logged
                logger.warning(f"Failed to send mailing to user {user_item.id}: {e}")
            
        logger.info(f"Finished mailing '{template_type}'. Sent to {sent_count}/{total_users} users.")
        return sent_count, total_users

    async def send_broadcast(self, text: str):
        """Sends a broadcast message to all non-banned users."""
        users = await self.user_repo.get_many({"is_banned": False}, limit=0)
        sent_count = 0
        total_users = len(users)
        logger.info(f"Starting broadcast to {total_users} users.")

        for user_item in users:
            try:
                await safe_send_message(self.bot, user_item.id, text)
                sent_count += 1
                await asyncio.sleep(0.05)
            except Exception as e:
                logger.warning(f"Failed to send broadcast to user {user_item.id}: {e}")
        
        logger.info(f"Finished broadcast. Sent to {sent_count}/{total_users} users.")
        return sent_count, total_users