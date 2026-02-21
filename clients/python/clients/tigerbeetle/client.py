import os
from tigerbeetle import (
    ClientSync,
    Account,
    Transfer,
    AccountFlags,
    CreateAccountResult,
    CreateTransferResult,
    id as tb_id,
)

# Configuration
TIGERBEETLE_CLUSTER_ID = int(os.environ.get("TIGERBEETLE_CLUSTER_ID", "0"))
TIGERBEETLE_ADDRESS = os.environ.get("TIGERBEETLE_ADDRESS", "127.0.0.1:3000")

# Ledger constants
EUR_LEDGER = 1
ACCOUNT_CODE_BUYER = 1
ACCOUNT_CODE_SELLER = 2
ACCOUNT_CODE_PLATFORM = 3
TRANSFER_CODE_PURCHASE = 1    # buyer -> platform
TRANSFER_CODE_SETTLEMENT = 2  # platform -> seller
PLATFORM_ESCROW_ACCOUNT_ID = 1

_client_instance = None


def get_tigerbeetle_client() -> ClientSync:
    """Returns a singleton instance of the TigerBeetle ClientSync."""
    global _client_instance
    if _client_instance is None:
        _client_instance = ClientSync(
            cluster_id=TIGERBEETLE_CLUSTER_ID,
            replica_addresses=TIGERBEETLE_ADDRESS,
        )
    return _client_instance


def _new_id() -> int:
    """Generate a new TigerBeetle-compatible 128-bit ID."""
    return tb_id()


def ensure_platform_account() -> None:
    """Create the platform escrow account (idempotent)."""
    client = get_tigerbeetle_client()
    results = client.create_accounts([
        Account(
            id=PLATFORM_ESCROW_ACCOUNT_ID,
            ledger=EUR_LEDGER,
            code=ACCOUNT_CODE_PLATFORM,
            flags=AccountFlags.NONE,
        ),
    ])
    for r in results:
        if r.result not in (CreateAccountResult.OK, CreateAccountResult.EXISTS):
            raise RuntimeError(f"Failed to create platform account: {r.result}")


def create_user_accounts() -> tuple[int, int]:
    """Create pending + settled accounts for a user. Returns (pending_id, settled_id)."""
    client = get_tigerbeetle_client()
    pending_id = _new_id()
    settled_id = _new_id()
    results = client.create_accounts([
        Account(
            id=pending_id,
            ledger=EUR_LEDGER,
            code=ACCOUNT_CODE_BUYER,
            flags=AccountFlags.NONE,
        ),
        Account(
            id=settled_id,
            ledger=EUR_LEDGER,
            code=ACCOUNT_CODE_BUYER,
            flags=AccountFlags.NONE,
        ),
    ])
    for r in results:
        if r.result not in (CreateAccountResult.OK, CreateAccountResult.EXISTS):
            raise RuntimeError(f"Failed to create user account: {r.result}")
    return pending_id, settled_id


def create_transfer(debit_id: int, credit_id: int, amount_cents: int, code: int) -> int:
    """Create a single transfer. Returns the transfer ID."""
    client = get_tigerbeetle_client()
    transfer_id = _new_id()
    results = client.create_transfers([
        Transfer(
            id=transfer_id,
            debit_account_id=debit_id,
            credit_account_id=credit_id,
            amount=amount_cents,
            ledger=EUR_LEDGER,
            code=code,
        ),
    ])
    for r in results:
        if r.result not in (CreateTransferResult.OK, CreateTransferResult.EXISTS):
            raise RuntimeError(f"Failed to create transfer: {r.result}")
    return transfer_id


def lookup_account_balance(account_id: int) -> dict:
    """Look up an account and return its balance fields."""
    client = get_tigerbeetle_client()
    accounts = client.lookup_accounts([account_id])
    if not accounts:
        return {}
    a = accounts[0]
    return {
        "debits_pending": a.debits_pending,
        "debits_posted": a.debits_posted,
        "credits_pending": a.credits_pending,
        "credits_posted": a.credits_posted,
    }
