import os
from tigerbeetle import Client

# Configuration
TIGERBEETLE_CLUSTER_ID = int(os.environ.get("TIGERBEETLE_CLUSTER_ID", "0"))
TIGERBEETLE_ADDRESS = os.environ.get("TIGERBEETLE_ADDRESS", "127.0.0.1:3000")

# Optional: configure concurrency max
CONCURRENCY_MAX = int(os.environ.get("TIGERBEETLE_CONCURRENCY_MAX", "32"))

_client_instance = None

def get_tigerbeetle_client() -> Client:
    """
    Returns a singleton instance of the TigerBeetle Client.
    Initializes the client on first call.
    """
    global _client_instance
    if _client_instance is None:
        _client_instance = Client(
            cluster_id=TIGERBEETLE_CLUSTER_ID, 
            replica_addresses=[TIGERBEETLE_ADDRESS],
            concurrency_max=CONCURRENCY_MAX
        )
    return _client_instance
