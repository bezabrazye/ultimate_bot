# services/channel_service.py
from typing import Optional, List, Tuple
from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from database.models import Channel, User
from database.repositories import UserRepository
from utils.misc import is_valid_telegram_link, extract_username_from_link
import logging

logger = logging.getLogger(__name__)

class ChannelService:
    def __init__(self, bot: Bot, user_repo: UserRepository):
        self.bot = bot
        self.user_repo = user_repo

    async def verify_and_add_channel(self, user: User, channel_link: str) -> Tuple[Optional[Channel], str, Optional[int]]:
        """
        Verifies a channel link and adds it to the user's channels.
        Returns: (Channel object or None, error_code, subscribers_count_if_any)
        """
        if not is_valid_telegram_link(channel_link):
            return None, "invalid_link", None

        chat_identifier = extract_username_from_link(channel_link)
        if not chat_identifier:
            # If it's a joinchat link without username, or direct chat ID
            # In such cases, bot must already be a member.
            logger.warning(f"Could not extract username from link: {channel_link}. Attempting to get chat by link as is.")
            try:
                # Attempt to get chat info directly using the link (works for @username_or_channel and some public links)
                chat = await self.bot.get_chat(channel_link) # Telegram API can resolve @username, t.me/channel, or chat_id
                chat_id = chat.id
            except Exception as e:
                logger.error(f"Failed to get chat info for link {channel_link}: {e}")
                return None, "invalid_link", None # If it's not a recognized link format again

        else:
            try:
                # Get chat by username / chat_id after extracting from link
                chat = await self.bot.get_chat(f"@{chat_identifier}")
                chat_id = chat.id
            except Exception as e:
                logger.error(f"Failed to get chat info for @{chat_identifier}: {e}")
                return None, "telegram_api_error", None


        if chat.type not in ['channel', 'group', 'supergroup']:
            return None, "not_channel_or_group", None

        # Check bot's permissions inside the channel
        try:
            bot_member = await self.bot.get_chat_member(chat_id, self.bot.id)
            if bot_member.status not in [ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR]:
                return None, "bot_not_admin_or_permissions", None

            # Need specific permissions for bot to function for boosting (e.g. invite users, post messages, get member list for some stats)
            # You might need to adjust these based on your booster logic needs
            required_permissions = bot_member.can_post_messages and bot_member.can_invite_users # Example permissions
            if not required_permissions:
                return None, "bot_not_admin_or_permissions", None

            # Check user's ownership/admin status
            member = await self.bot.get_chat_member(chat_id, user.id)
            if member.status not in [ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR]:
                return None, "not_owner", None

            # Re-fetch full chat details to get subscriber count
            # For private groups/channels, members_count might not be accurate or available without specific permissions
            # or if the bot itself isn't a creator/owner with full rights.
            subscribers_count = chat.members_count # Direct attribute from get_chat()
            if subscribers_count < 100:
                return None, "not_enough_subscribers", subscribers_count

            # Check if channel already added to THIS user
            if any(c.id == chat_id for c in user.channels):
                return None, "channel_already_added", None
            
            # Check user's slots for adding a new channel
            current_channels_count = len(user.channels)
            if current_channels_count >= user.max_channels_slots:
                return None, "max_channels_reached", None


            new_channel = Channel(
                id=chat_id,
                title=chat.title,
                username=chat.username,
                link=chat.invite_link or f"https://t.me/{chat.username}" if chat.username else f"https://t.me/c/{str(chat_id)[4:]}", # Heuristic for invite link
                owner_id=user.id,
                subscribers_count=subscribers_count # Use directly from chat object
            )

            success = await self.user_repo.add_channel_to_user(user, new_channel)
            if success:
                logger.info(f"User {user.id} added channel {new_channel.title} ({new_channel.id}).")
                return new_channel, "success", None
            else:
                return None, "db_error", None # Failed to save to DB

        except Exception as e:
            logger.error(f"Error during channel verification for {channel_link} (user {user.id}): {e}", exc_info=True)
            return None, "error_checking_channel", None

    async def get_user_channels(self, user: User) -> List[Channel]:
        # Channels are embedded in User model
        return user.channels

    async def get_channel_statistics(self, channel: Channel) -> dict:
        """
        Placeholder for fetching detailed channel statistics.
        This would involve:
        - Getting `get_chat_members_count` from Telegram.
        - Potentially fetching past posts and their `views` and `forwards` counts (limited by Bot API).
        """
        try:
            chat = await self.bot.get_chat(channel.id)
            subscribers_count = chat.members_count
            # Example of what could be returned
            stats = {
                "subscribers_count": subscribers_count,
                "daily_growth_avg": "N/A (needs historical data)",
                "views_per_post_avg": "N/A (needs message fetching)",
                "activity_level": "N/A (needs message interaction analysis)",
            }
            return stats
        except Exception as e:
            logger.error(f"Error getting stats for channel {channel.id}: {e}", exc_info=True)
            return {"error": "Could not fetch stats."}

    async def update_channel_analysis(self, channel: Channel, analysis_report: str) -> None:
        # This would be called after AI analysis is done
        pass # Not implemented fully in this draft