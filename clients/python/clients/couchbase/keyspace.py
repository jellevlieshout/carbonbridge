import uuid
from dataclasses import dataclass
from typing import Optional
from couchbase.result import MutationResult
from couchbase.options import QueryOptions
from .config import get_cluster, DEFAULT_BUCKET_NAME

@dataclass
class Keyspace:
    bucket_name: str
    scope_name: str
    collection_name: str

    @classmethod
    def from_string(cls, keyspace: str) -> 'Keyspace':
        parts = keyspace.split('.')
        if len(parts) != 3:
            raise ValueError(
                "Invalid keyspace format. Expected 'bucket_name.scope_name.collection_name', "
                f"got '{keyspace}'"
            )
        return cls(*parts)

    def __str__(self) -> str:
        return f"{self.bucket_name}.{self.scope_name}.{self.collection_name}"

    async def query(self, query: str, **kwargs) -> list:
        cluster = await get_cluster()
        query = query.replace("${keyspace}", str(self))
        options = QueryOptions(**kwargs)
        result = cluster.query(query, options)
        return [row async for row in result]

    async def get_scope(self):
        cluster = await get_cluster()
        bucket = cluster.bucket(self.bucket_name)
        return bucket.scope(self.scope_name)

    async def get_collection(self):
        scope = await self.get_scope()
        return scope.collection(self.collection_name)

    async def insert(self, value: dict, key: Optional[str] = None, **kwargs) -> MutationResult:
        if key is None:
            key = str(uuid.uuid4())
        collection = await self.get_collection()
        return await collection.insert(key, value, **kwargs)

    async def upsert(self, key: str, value: dict, **kwargs) -> MutationResult:
        """Insert or update a document (idempotent write).
        
        Args:
            key: Document key (required for idempotency)
            value: Document value to store
            **kwargs: Additional options passed to collection.upsert()
            
        Returns:
            MutationResult from the upsert operation
        """
        collection = await self.get_collection()
        return await collection.upsert(key, value, **kwargs)

    async def remove(self, key: str, **kwargs) -> int:
        collection = await self.get_collection()
        result = await collection.remove(key, **kwargs)
        return result.cas

    async def list(self, limit: Optional[int] = None) -> list:
        limit_clause = f" LIMIT {limit}" if limit is not None else ""
        query = f"SELECT META().id, * FROM {self}{limit_clause}"
        return await self.query(query)

def get_keyspace(collection_name: str, scope_name: Optional[str] = "_default", bucket_name: Optional[str] = DEFAULT_BUCKET_NAME) -> Keyspace:
    """
    Create a Keyspace instance with optional scope and bucket parameters.
    
    Args:
        collection_name: Name of the collection
        scope_name: Name of the scope (defaults to "_default")
        bucket_name: Name of the bucket (defaults to DEFAULT_BUCKET_NAME)
        
    Returns:
        Keyspace instance
    """
    return Keyspace(bucket_name, scope_name, collection_name)

async def get_collection(keyspace: Keyspace):
    """
    Get a collection based on a Keyspace instance.
    
    Args:
        keyspace: Keyspace instance containing bucket, scope, and collection names
        
    Returns:
        Couchbase Collection object
        
    Raises:
        couchbase.exceptions.BucketNotFoundException: If bucket doesn't exist
        couchbase.exceptions.ScopeNotFoundException: If scope doesn't exist
        couchbase.exceptions.CollectionNotFoundException: If collection doesn't exist
    """
    cluster = await get_cluster()
    bucket = cluster.bucket(keyspace.bucket_name)
    scope = bucket.scope(keyspace.scope_name)
    return scope.collection(keyspace.collection_name)
