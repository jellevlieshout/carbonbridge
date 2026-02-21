class ResonateClientError(Exception):
    """Base exception for ResonateClient."""
    pass


class ResonateConnectionError(ResonateClientError):
    """Raised when connection to the Resonate server fails."""
    pass


class ResonateRPCError(ResonateClientError):
    """Raised when an RPC call fails."""
    pass
