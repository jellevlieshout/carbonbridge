from typing import Dict, Optional, Literal
from pydantic import BaseModel
from clients.couchbase import BaseModelCouchbase, BaseCouchbaseEntityData

class UserData(BaseCouchbaseEntityData):
    email: str

class User(BaseModelCouchbase[UserData]):
    _collection_name = "users"
