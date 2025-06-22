# database/repositories.py
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional, List, Dict, Any, Type, TypeVar
from bson import ObjectId
from datetime import datetime
from pydantic import BaseModel


from database.models import User, Channel, Order, Transaction, PromoCode, BoosterAccount

T = TypeVar('T', bound=BaseModel) # Generic type variable for BaseModel

class BaseRepository:
    def __init__(self, db_client: AsyncIOMotorClient, collection_name: str, model: Type[T]):
        self.collection = db_client[collection_name]
        self.model = model

    async def get_by_id(self, item_id: Any) -> Optional[T]:
        data = await self.collection.find_one({"_id": item_id})
        return self.model(**data) if data else None

    async def get_one(self, query: Dict[str, Any]) -> Optional[T]:
        data = await self.collection.find_one(query)
        return self.model(**data) if data else None

    async def get_many(self, query: Dict[str, Any], limit: int = 0) -> List[T]:
        cursor = self.collection.find(query)
        if limit > 0:
            cursor = cursor.limit(limit)
        data_list = await cursor.to_list(length=None)
        return [self.model(**item) for item in data_list]

    async def create(self, item: T) -> Optional[T]:
        data = item.model_dump(by_alias=True, exclude_unset=True)
        result = await self.collection.insert_one(data)
        if result.acknowledged:
            return item
        return None

    async def update(self, query: Dict[str, Any], update_data: Dict[str, Any]) -> int:
        result = await self.collection.update_one(query, {"$set": update_data})
        return result.modified_count

    async def update_many(self, query: Dict[str, Any], update_data: Dict[str, Any]) -> int:
        result = await self.collection.update_many(query, {"$set": update_data})
        return result.modified_count

    async def delete(self, query: Dict[str, Any]) -> int:
        result = await self.collection.delete_one(query)
        return result.deleted_count

    async def increment(self, query: Dict[str, Any], field: str, value: int = 1) -> int:
        result = await self.collection.update_one(query, {"$inc": {field: value}})
        return result.modified_count

class UserRepository(BaseRepository):
    def __init__(self, db_client: AsyncIOMotorClient):
        super().__init__(db_client, "users", User)

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        return await self.get_by_id(user_id)

    async def create_user(self, user_data: User) -> Optional[User]:
        return await self.create(user_data)

    async def update_user(self, user_id: int, update_data: Dict[str, Any]) -> int:
        return await self.update({"_id": user_id}, update_data)

    async def increment_balance(self, user_id: int, amount: int) -> int:
        return await self.increment({"_id": user_id}, "balance", amount)

    async def add_channel_to_user(self, user_id: int, channel: Channel) -> int:
        return (await self.collection.update_one(
            {"_id": user_id},
            {"$push": {"channels": channel.model_dump(by_alias=True, exclude_unset=True)}}
        )).modified_count

    async def remove_channel_from_user(self, user_id: int, channel_id: int) -> int:
        return (await self.collection.update_one(
            {"_id": user_id},
            {"$pull": {"channels": {"id": channel_id}}}
        )).modified_count

    async def add_used_promocode(self, user_id: int, promo_name: str) -> int:
        return (await self.collection.update_one(
            {"_id": user_id},
            {"$addToSet": {"promo_codes_used": promo_name}}
        )).modified_count

    async def has_used_promocode(self, user_id: int, promo_name: str) -> bool:
        user = await self.get_user_by_id(user_id)
        return user and promo_name in user.promo_codes_used

    async def add_ip_serial(self, user_id: int, ip: Optional[str], serial: Optional[str]) -> int:
        # Note: IP/Serial not directly available from bot API.
        update_doc = {}
        if ip: update_doc["$addToSet"] = {"ip_addresses": ip}
        if serial: 
            if "$addToSet" not in update_doc: update_doc["$addToSet"] = {}
            update_doc["$addToSet"]["serial_numbers"] = serial
        if update_doc:
            return (await self.collection.update_one({"_id": user_id}, update_doc)).modified_count
        return 0

class OrderRepository(BaseRepository):
    def __init__(self, db_client: AsyncIOMotorClient):
        super().__init__(db_client, "orders", Order)

    async def get_order_by_id(self, order_id: str) -> Optional[Order]:
        return await self.get_by_id(order_id)

    async def create_order(self, order_data: Order) -> Optional[Order]:
        return await self.create(order_data)

    async def get_user_orders(self, user_id: int, status_filter: Optional[str] = None) -> List[Order]:
        query = {"user_id": user_id}
        if status_filter:
            query["status"] = status_filter
        return await self.get_many(query, limit=0)

class TransactionRepository(BaseRepository):
    def __init__(self, db_client: AsyncIOMotorClient):
        super().__init__(db_client, "transactions", Transaction)

    async def get_transaction_by_id(self, tx_id: str) -> Optional[Transaction]:
        return await self.get_by_id(tx_id)

    async def create_transaction(self, tx_data: Transaction) -> Optional[Transaction]:
        return await self.create(tx_data)

    async def update_transaction(self, tx_id: str, update_data: Dict[str, Any]) -> int:
        return await self.update({"_id": tx_id}, update_data)

    async def get_transaction_by_cryptomus_uuid(self, cryptomus_uuid: str) -> Optional[Transaction]:
        return await self.get_one({"cryptomus_uuid": cryptomus_uuid})

class PromoCodeRepository(BaseRepository):
    def __init__(self, db_client: AsyncIOMotorClient):
        super().__init__(db_client, "promo_codes", PromoCode)

    async def get_promo_code_by_name(self, name: str) -> Optional[PromoCode]:
        return await self.get_by_id(name.upper())

    async def create_promo_code(self, promo_data: PromoCode) -> Optional[PromoCode]:
        return await self.create(promo_data)

    async def update_promo_code(self, name: str, update_data: Dict[str, Any]) -> int:
        return await self.update({"_id": name.upper()}, update_data)

    async def increment_activations(self, name: str) -> int:
        return await self.increment({"_id": name.upper()}, "activations_used")

class BoosterAccountRepository(BaseRepository):
    def __init__(self, db_client: AsyncIOMotorClient):
        super().__init__(db_client, "booster_accounts", BoosterAccount)

    async def create_booster_account(self, account_data: BoosterAccount) -> BoosterAccount:
        return await self.create(account_data)

    async def get_booster_account_by_phone(self, phone: str) -> Optional[BoosterAccount]:
        return await self.get_by_id(phone)

    async def get_all_active_booster_accounts(self) -> List[BoosterAccount]:
        return await self.get_many({"status": "active"}, limit=0)
