# utils/logger.py
import logging

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("bot.log", encoding="utf-8"),
            logging.StreamHandler()
        ]
    )
    logging.getLogger('httpx').setLevel(logging.WARNING) # Reduce noise from HTTPX
    logging.getLogger('aiogram').setLevel(logging.INFO) # Aiogram can be noisy
    logging.getLogger('motor').setLevel(logging.WARNING)
    logging.getLogger('APScheduler').setLevel(logging.INFO)