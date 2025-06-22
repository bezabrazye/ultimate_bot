# bot.py
import asyncio

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage # Or RedisStorage for production
from aiogram.enums import ParseMode
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler # Import for scheduler
from pathlib import Path # Add this import for path manipulation within i18n setup

# Project imports
from config.settings import settings
from database.db import MongoDB # Corrected to MongoDB class
from database.repositories import UserRepository, OrderRepository, TransactionRepository, PromoCodeRepository, BoosterAccountRepository

# Middlewares
from middlewares.user_middleware import UserMiddleware
from middlewares.i18n_middleware import UserI18nMiddleware
from middlewares.auth_middleware import AuthMiddleware

# i18n setup
# --- PATCH START ---
# Import the i18n_manager from your i18n.py file
from i18n import i18n_manager
# --- PATCH END ---

# Utilities
from utils.logger import setup_logging

# Services
from services.user_service import UserService
from services.channel_service import ChannelService
from services.order_service import OrderService
from services.payment_service import PaymentService
from services.admin_service import AdminService
from services.mailing_service import MailingService
from services.ai_service import AIService
from services.webapp_service import WebAppService # NEW

# Handlers imports
from handlers.private import (
    start,
    language,
    channel_setup,
    main_menu,
    boosting,
    account, # Will contain WebApp button
    wallet,
    offers
)
from handlers.admin import admin_panel
from handlers.callbacks import router as global_callbacks_router # Import common callback router itself

# Scheduler tasks setup
from tasks.scheduler import setup_scheduler as setup_background_scheduler

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

async def on_startup(bot: Bot, dispatcher: Dispatcher):
    # Ensure MongoDB connection is initialized globally first
    await MongoDB().connect() # Connect using the global instance

    # Initialize repositories
    user_repo = UserRepository(MongoDB().db)
    order_repo = OrderRepository(MongoDB().db)
    transaction_repo = TransactionRepository(MongoDB().db)
    promo_repo = PromoCodeRepository(MongoDB().db)
    booster_account_repo = BoosterAccountRepository(MongoDB().db)

    # Initialize services
    user_service = UserService(user_repo, promo_repo)
    channel_service = ChannelService(bot, user_repo)
    order_service = OrderService(order_repo, user_repo)
    payment_service = PaymentService(user_repo, transaction_repo)
    admin_service = AdminService(user_repo, order_repo, transaction_repo, promo_repo, booster_account_repo)
    mailing_service = MailingService(bot, user_repo)
    ai_service = AIService()
    webapp_service = WebAppService(user_repo) # NEW

    # Pass services and repositories to handlers via data
    # This makes them available in the `data` dictionary of handler functions
    dispatcher["user_repo"] = user_repo
    dispatcher["user_service"] = user_service
    dispatcher["channel_service"] = channel_service
    dispatcher["order_service"] = order_service
    dispatcher["payment_service"] = payment_service
    dispatcher["admin_service"] = admin_service
    dispatcher["mailing_service"] = mailing_service
    dispatcher["ai_service"] = ai_service
    dispatcher["webapp_service"] = webapp_service # NEW

    # Setup background scheduler tasks
    # Passing the global MongoDB instance to scheduler tasks
    await setup_background_scheduler(mailing_service, payment_service)

    logger.info("Bot started successfully!")

async def on_shutdown(bot: Bot, dispatcher: Dispatcher):
    await MongoDB().close() # Close connection using the global instance
    logger.info("Bot shutting down.")
    # Ensure scheduler is shut down properly
    scheduler = dispatcher.get("apscheduler.scheduler")
    if scheduler:
        scheduler.shutdown()
        logger.info("APScheduler shut down.")

async def main():
    # Initialize Bot and Dispatcher
    bot = Bot(token=settings.BOT_TOKEN, parse_mode=ParseMode.HTML)
    storage = MemoryStorage() # Use RedisStorage for production: `RedisStorage.from_url("redis://localhost:6379/1")`
    dp = Dispatcher(storage=storage)

    # Register middlewares
    # Order for outer_middleware is important:
    # 1. Official aiogram_i18n middleware (i18n_manager itself) should be registered first.
    #    This sets up the primary i18n context (like locale detection from user settings)
    #    and makes the 'i18n' object available in handler data.
    # 2. UserMiddleware: If it provides 'user' and 'user_repo' in 'data' dictionary,
    #    and your UserI18nMiddleware relies on them, then UserMiddleware must run before.
    # 3. UserI18nMiddleware: Your custom middleware which then overrides/refines the locale
    #    based on your database user preferences.

    # --- PATCH START ---
    # Register the aiogram_i18n.I18n instance from your i18n.py file as a middleware
    dp.update.outer_middleware(i18n_manager) # Make sure this is one of the first outer_middlewares
    # --- PATCH END ---

    dp.update.outer_middleware(UserMiddleware())
    # Pass the i18n_manager instance (which is your aiogram_i18n.I18n object)
    # to your custom UserI18nMiddleware.
    dp.update.outer_middleware(UserI18nMiddleware(i18n_manager))

    dp.message.middleware(AuthMiddleware())
    # dp.callback_query.middleware(AuthMiddleware()) # AuthMiddleware also applies to callbacks, no need to duplicate

    # Register routers (handlers)
    dp.include_router(start.router)
    dp.include_router(language.router)
    dp.include_router(channel_setup.router)
    dp.include_router(main_menu.router)
    dp.include_router(boosting.router)
    dp.include_router(account.router)
    dp.include_router(wallet.router)
    dp.include_router(offers.router)
    dp.include_router(admin_panel.router) # Admin panel router
    dp.include_router(global_callbacks_router) # Common callbacks like go to main menu

    # Register startup/shutdown hooks
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Start polling
    logger.info("Starting bot polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped manually by KeyboardInterrupt.")
    except Exception as e:
        logger.error(f"Bot encountered unhandled error: {e}", exc_info=True)
