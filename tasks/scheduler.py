# tasks/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import logging
from datetime import datetime, timedelta
import random

from services.mailing_service import MailingService
from services.payment_service import PaymentService # For background payment checks (less critical if webhooks work)
from database.db import mongo_db
from database.repositories import UserRepository, TransactionRepository # Add transaction repo

logger = logging.getLogger(__name__)

async def setup_scheduler(mailing_service: MailingService, payment_service: PaymentService):
    scheduler = AsyncIOScheduler()

    # Schedule daily random mailings (1 morning, 1 evening)
    # Example: morning at 9-10 AM, evening at 8-9 PM
    for i in range(14): # 14 templates, randomize two per day
        template_types = list(MailingService.MAILING_TEMPLATES.keys())
        # Pick 2 random types for daily mailings, ensure different
        chosen_types = random.sample(template_types, 2)
        
        # Morning mailing
        scheduler.add_job(
            mailing_service.send_random_mailing,
            "cron",
            hour=random.randint(9, 10), # Between 9 AM and 10 AM
            minute=random.randint(0, 59),
            args=[chosen_types[0]],
            id=f"daily_mailing_morning_{i}",
            name=f"Daily mailing ({chosen_types[0]}) morning",
            replace_existing=True
        )
        logger.info(f"Scheduled morning mailing '{chosen_types[0]}' for {i} day.")

        # Evening mailing
        scheduler.add_job(
            mailing_service.send_random_mailing,
            "cron",
            hour=random.randint(20, 21), # Between 8 PM and 9 PM
            minute=random.randint(0, 59),
            args=[chosen_types[1]],
            id=f"daily_mailing_evening_{i}",
            name=f"Daily mailing ({chosen_types[1]}) evening",
            replace_existing=True
        )
        logger.info(f"Scheduled evening mailing '{chosen_types[1]}' for {i} day.")

    # Schedule periodic check for pending Cryptomus payments (fallback for webhooks)
    # This should be less frequent if webhooks are reliable
    scheduler.add_job(
        check_pending_payments,
        "interval",
        minutes=5, # Check every 5 minutes
        args=[payment_service],
        id="check_pending_payments",
        name="Check Cryptomus pending payments",
        replace_existing=True
    )
    logger.info("Scheduled task to check pending payments every 5 minutes.")

    scheduler.start()
    logger.info("Scheduler started.")

async def check_pending_payments(payment_service: PaymentService):
    """Task to periodically check pending payments that might have been missed by webhooks."""
    logger.info("Running scheduled check for pending Cryptomus payments.")
    
    # Get outstanding transactions that are still pending and not expired
    # Re-accessing repos via mongo_db for tasks if they are not passed directly
    transaction_repo = TransactionRepository(mongo_db.db)
    
    # Get pending transactions that are not past their expiration
    pending_transactions = await transaction_repo.get_many(
        {"status": "pending", "expires_at": {"$gt": datetime.now()}},
        limit=0
    )

    checked_count = 0
    for tx in pending_transactions:
        try:
            # Cryptomus check_status already updates DB and returns status
            updated_tx = await payment_service.check_cryptomus_payment_status(tx.cryptomus_uuid)
            if updated_tx and updated_tx.status == "completed":
                logger.info(f"Payment for transaction {tx.id} ({tx.cryptomus_uuid}) confirmed via scheduled check.")
                checked_count += 1
            elif updated_tx and updated_tx.status == "failed":
                 logger.info(f"Payment for transaction {tx.id} ({tx.cryptomus_uuid}) failed/expired via scheduled check.")
                 checked_count += 1
        except Exception as e:
            logger.error(f"Error checking status for transaction {tx.id}: {e}", exc_info=True)
    logger.info(f"Finished checking {len(pending_transactions)} pending payments. {checked_count} updated.")

2.24 handlers/__init__.py
# handlers/__init__.py
# Import all handler modules to ensure their routers are registered when bot.py imports them.
# The actual registration happens in bot.py using dp.include_router()

from . import private
from . import admin
from . import callbacks # Contains common callback handlers
