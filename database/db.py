# database/db.py (изменился, чтобы быть глобальным инстансом)
from motor.motor_asyncio import AsyncIOMotorClient
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

class MongoDB:
    _instance = None # Singleton instance
    client: AsyncIOMotorClient = None
    db = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(MongoDB, cls).__new__(cls)
        return cls._instance

    async def connect(self):
        if self.client is None: # Only connect if not already connected
            try:
                self.client = AsyncIOMotorClient(settings.MONGO_URI, maxPoolSize=100)
                await self.client.admin.command('ping') # Test connection
                self.db = self.client[settings.MONGO_DB_NAME]
                logger.info(f"Connected to MongoDB: {settings.MONGO_URI} (DB: {settings.MONGO_DB_NAME})")
            except Exception as e:
                logger.error(f"Failed to connect to MongoDB: {e}")
                raise
        else:
            logger.info("MongoDB client already connected.")

    async def close(self):
        if self.client:
            self.client.close()
            self.client = None # Reset client
            self.db = None     # Reset db
            logger.info("MongoDB connection closed.")

# Instantiate the singleton immediately
mongo_db = MongoDB()

async def get_db():
    # This getter should check if connection is establised and if not, try to establish.
    # For now, it relies on on_startup to establish.
    if mongo_db.db is None:
        await mongo_db.connect() # Ensure connection is active
    return mongo_db.db
