import os
import asyncio
from datetime import timedelta
from couchbase.auth import PasswordAuthenticator
from acouchbase.cluster import Cluster as AsyncCluster
from couchbase.options import ClusterOptions

# Environment variables
USERNAME = os.environ.get('COUCHBASE_USERNAME', '')
PASSWORD = os.environ.get('COUCHBASE_PASSWORD', '')
DEFAULT_BUCKET_NAME = os.environ.get('COUCHBASE_BUCKET', '')
HOST = os.environ.get('COUCHBASE_HOST', '')
PROTOCOL = os.environ.get('COUCHBASE_PROTOCOL', '')

# Validation
errors = []
if not USERNAME:
    errors.append("COUCHBASE_USERNAME is missing or empty")
if not PASSWORD:
    errors.append("COUCHBASE_PASSWORD is missing or empty")
if not HOST:
    errors.append("COUCHBASE_HOST is missing or empty")
if not DEFAULT_BUCKET_NAME:
    errors.append("COUCHBASE_BUCKET is missing or empty")

valid_protocols = ('couchbase', 'couchbases')
if PROTOCOL not in valid_protocols:
    errors.append(f"COUCHBASE_PROTOCOL '{PROTOCOL}' is invalid. Must be one of {valid_protocols}")

if errors:
    raise ValueError(f"Invalid Couchbase Configuration:\n" + "\n".join(errors))

# Authentication setup
auth = PasswordAuthenticator(
    USERNAME,
    PASSWORD
)

# Module-level cluster cache
_cluster = None

async def get_cluster(max_retries: int = 10, initial_delay: float = 1.0, max_delay: float = 30.0):
    """
    Returns a cached Couchbase cluster connection.
    Creates a new connection if one doesn't exist.
    Implements retry with exponential backoff for startup race conditions.
    """
    global _cluster
    if _cluster is None:
        url = PROTOCOL + "://" + HOST
        delay = initial_delay
        last_exception = None
        
        for attempt in range(1, max_retries + 1):
            try:
                _cluster = await AsyncCluster.connect(url, ClusterOptions(auth))
                break
            except Exception as e:
                last_exception = e
                if attempt < max_retries:
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, max_delay)  # Exponential backoff with cap
                else:
                    raise last_exception
        
        await _cluster.wait_until_ready(timedelta(seconds=50))
    return _cluster

async def get_default_bucket():
    """
    Returns the default bucket using the cached cluster connection.
    """
    cluster = await get_cluster()
    return cluster.bucket(DEFAULT_BUCKET_NAME)

async def check_connection():
    """
    Explicitly checks the connection to the Couchbase cluster.
    Useful for startup checks.
    """
    cluster = await get_cluster()
    await cluster.ping()
