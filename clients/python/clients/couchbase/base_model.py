import uuid
from datetime import datetime, timezone
from typing import Tuple, Optional, TypeVar, Generic, List, ClassVar
from pydantic import BaseModel
from couchbase.exceptions import DocumentNotFoundException
from .keyspace import Keyspace, get_keyspace

class BaseCouchbaseEntityData(BaseModel):
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by_user_id: Optional[str] = None

DataT = TypeVar("DataT", bound=BaseCouchbaseEntityData)
T = TypeVar("T", bound="BaseModelCouchbase")

class BaseModelCouchbase(BaseModel, Generic[DataT]):
    id: str
    data: DataT
    cas: Optional[int] = None

    _collection_name: ClassVar[str] = ""

    @staticmethod
    def model_dump_with_excluded_attributes(data: DataT) -> dict:
        """
        Converts the model to a dictionary for database storage,
        ensuring fields marked with exclude=True are included.
        """
        # 1. Standard dump to handle serialization (enums, datetimes, etc.)
        doc = data.model_dump(mode='json')
        
        # 2. Re-inject fields that were excluded
        for field_name, field_info in data.model_fields.items():
            if field_info.exclude:
                 value = getattr(data, field_name)
                 if value is not None:
                      # We assign the raw value. This works for primitives (str, int).
                      # If you have excluded Enums or nested Models, we might need value.value or value.model_dump()
                      # But for 'api_key' (str), this is perfect.
                      doc[field_name] = value
        return doc

    @classmethod
    def get_keyspace(cls) -> Keyspace:
        if not cls._collection_name:
            raise ValueError(f"_collection_name not set for {cls.__name__}")
        return get_keyspace(cls._collection_name)

    @classmethod
    async def get(cls: type[T], id: str) -> Optional[T]:
        try:
            collection = await cls.get_keyspace().get_collection()
            result = await collection.get(id)
            data = result.content_as[dict]
            return cls(id=id, data=data, cas=result.cas)
        except DocumentNotFoundException:
            return None

    @classmethod
    async def create(cls: type[T], data: DataT, key: Optional[str] = None, user_id: Optional[str] = None) -> T:
        if key is None:
            key = str(uuid.uuid4())
        
        now = datetime.now(timezone.utc)
        if data.created_at is None:
            data.created_at = now
        data.updated_at = now
        
        if user_id:
            data.created_by_user_id = user_id

        doc = cls.model_dump_with_excluded_attributes(data)
        result = await cls.get_keyspace().insert(doc, key=key)
        return cls(id=key, data=data, cas=result.cas)

    @classmethod
    async def create_or_update(cls: type[T], key: str, data: DataT, user_id: Optional[str] = None) -> T:
        """Idempotently create or update a document with a specific key.
        
        This method uses upsert semantics - if the document exists, it will be
        updated; if not, it will be created. This is essential for retry-safe
        operations in durable execution contexts like Resonate.
        
        Args:
            key: Deterministic document key for idempotency
            data: The entity data to store
            user_id: Optional user ID to associate with the document
            
        Returns:
            The created or updated entity
        """
        now = datetime.now(timezone.utc)
        if data.created_at is None:
            data.created_at = now
        data.updated_at = now
        
        if user_id:
            data.created_by_user_id = user_id

        doc = cls.model_dump_with_excluded_attributes(data)
        keyspace = cls.get_keyspace()
        result = await keyspace.upsert(key, doc)
        return cls(id=key, data=data, cas=result.cas)

    @classmethod
    async def update(cls: type[T], item: T) -> T:
        collection = await cls.get_keyspace().get_collection()
        
        item.data.updated_at = datetime.now(timezone.utc)
        
        doc = cls.model_dump_with_excluded_attributes(item.data)
        if item.cas:
            from couchbase.options import ReplaceOptions
            result = await collection.replace(item.id, doc, ReplaceOptions(cas=item.cas))
            item.cas = result.cas
        else:
            result = await collection.replace(item.id, doc)
            item.cas = result.cas
        return item

    @classmethod
    async def delete(cls: type[T], id: str) -> bool:
        try:
            await cls.get_keyspace().remove(id)
            return True
        except DocumentNotFoundException:
            return False

    @classmethod
    async def list(cls: type[T], limit: Optional[int] = None) -> List[T]:
        rows = await cls.get_keyspace().list(limit=limit)
        items = []
        for row in rows:
            # Row structure: {'id': '...', 'collection_name': {...}} or similar
            # Extract data using collection name
            data_dict = row.get(cls._collection_name)
            if data_dict is None:
                # Fallback: try to find the data in other keys if needed? 
                # For now assuming standard behavior
                pass
            
            if data_dict:
                items.append(cls(id=row['id'], data=data_dict))
        return items

    @classmethod
    async def get_many(cls: type[T], ids: List[str]) -> List[T]:
        # TODO: Batch implementation when available. Loop for now.
        # This is strictly "get", failing if not found? 
        # Or should it return None for missing?
        # N1QL approach: SELECT META().id, * FROM keyspace USE KEYS [...]
        keyspace = cls.get_keyspace()
        # Use N1QL for batch get
        keys_str = ", ".join([f'"{k}"' for k in ids])
        query = f"SELECT META().id, * FROM {keyspace} USE KEYS [{keys_str}]"
        rows = await keyspace.query(query)
        
        items = []
        for row in rows:
            data_dict = row.get(cls._collection_name)
            if data_dict:
                items.append(cls(id=row['id'], data=data_dict))
        return items

    @classmethod
    async def create_many(cls: type[T], items: List[DataT], user_id: Optional[str] = None) -> List[T]:
        keyspace = cls.get_keyspace()
        results = []
        now = datetime.now(timezone.utc)
        for data in items:
            key = str(uuid.uuid4())
            if data.created_at is None:
                data.created_at = now
            data.updated_at = now
            if user_id:
                data.created_by_user_id = user_id
            doc = cls.model_dump_with_excluded_attributes(data)
            await keyspace.insert(doc, key=key)
            results.append(cls(id=key, data=data))
        return results

    @classmethod
    async def update_many(cls: type[T], items: List[T]) -> List[T]:
        from couchbase.options import ReplaceOptions
        keyspace = cls.get_keyspace()
        collection = await keyspace.get_collection()
        results = []
        now = datetime.now(timezone.utc)
        for item in items:
            item.data.updated_at = now
            doc = cls.model_dump_with_excluded_attributes(item.data)
            await collection.replace(item.id, doc)
            results.append(item)
        return results

    @classmethod
    async def delete_many(cls: type[T], ids: List[str]) -> List[str]:
        keyspace = cls.get_keyspace()
        params = {"keys": ids}
        # N1QL DELETE: DELETE FROM keyspace USE KEYS $keys
        # But we need to use parametrized query.
        # Wait, simple loop remove is safer/easier for now.
        deleted = []
        for key in ids:
            try:
                await keyspace.remove(key)
                deleted.append(key)
            except Exception:
                pass
        return deleted
