# database/db.py
from motor.motor_asyncio import AsyncIOMotorClient
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

class MongoDB:
    client: AsyncIOMotorClient = None
    db = None

    async def connect(self):
        try:
            self.client = AsyncIOMotorClient(settings.MONGO_URI, maxPoolSize=100)
            await self.client.admin.command('ping') # Test connection
            self.db = self.client[settings.MONGO_DB_NAME]
            logger.info(f"Connected to MongoDB: {settings.MONGO_URI} (DB: {settings.MONGO_DB_NAME})")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    async def close(self):
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed.")

mongo_db = MongoDB()

async def get_db():
    return mongo_db.db