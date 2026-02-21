from .config import (
    USERNAME,
    PASSWORD,
    DEFAULT_BUCKET_NAME,
    HOST,
    PROTOCOL,
    auth,
    get_cluster,
    get_default_bucket,
    check_connection
)
from .keyspace import (
    Keyspace,
    get_keyspace,
    get_collection
)
from .base_model import (
    BaseModelCouchbase,
    BaseCouchbaseEntityData,
    DataT,
    T
)

# External re-exports to match original API
import couchbase.subdocument as SD
from couchbase.auth import PasswordAuthenticator
from acouchbase.cluster import Cluster as AsyncCluster
from couchbase.options import (ClusterOptions, ClusterTimeoutOptions, QueryOptions, MutateInOptions)
from couchbase.exceptions import ScopeAlreadyExistsException, CollectionAlreadyExistsException, DocumentNotFoundException, CASMismatchException
from couchbase.management.collections import CreateCollectionSettings
from couchbase.result import MutationResult
from typing import Tuple, Optional, TypeVar, Generic, List, ClassVar
from pydantic import BaseModel, Field
import os
import uuid
from datetime import timedelta
from dataclasses import dataclass
