import asyncio
from typing import Any, Dict, List, Literal, Optional, Tuple

from models.entities.couchbase.users import BuyerProfile, User, UserData


async def user_get_data_for_frontend(user_id: str) -> Dict[str, Any]:
    user = await User.get(user_id)
    if not user:
        raise ValueError(f"User with ID {user_id} not found")
    return {"user": user.data.model_dump()}


async def user_create_if_not_exists_and_get(user_id: str, email: str) -> User:
    existing_user = await User.get(user_id)
    if existing_user:
        return existing_user
    new_user_data = UserData(email=email)
    return await User.create(new_user_data, key=user_id, user_id=user_id)


async def user_get_by_email(email: str) -> Optional[User]:
    keyspace = User.get_keyspace()
    rows = await keyspace.query(
        f"SELECT META().id, * FROM {keyspace} WHERE email = $email", email=email
    )
    for row in rows:
        data_dict = row.get("users")
        if data_dict:
            return User(id=row["id"], data=data_dict)
    return None


async def user_register(
    email: str,
    hashed_password: str,
    role: Literal["buyer", "seller", "both", "admin"],
    **kwargs,
) -> User:
    data = UserData(
        email=email,
        hashed_password=hashed_password,
        role=role,
        **kwargs,
    )
    return await User.create(data)


async def user_update_onboarding(user_id: str, data: dict) -> User:
    user = await User.get(user_id)
    if not user:
        raise ValueError(f"User with ID {user_id} not found")

    allowed_fields = {
        "role",
        "company_name",
        "company_size_employees",
        "sector",
        "country",
    }
    for key, value in data.items():
        if key in allowed_fields:
            setattr(user.data, key, value)

    if "buyer_profile" in data and data["buyer_profile"]:
        user.data.buyer_profile = BuyerProfile(**data["buyer_profile"])

    return await User.update(user)


async def user_update_buyer_profile(user_id: str, profile: BuyerProfile) -> User:
    user = await User.get(user_id)
    if not user:
        raise ValueError(f"User with ID {user_id} not found")
    user.data.buyer_profile = profile
    return await User.update(user)


async def user_get_buyer_profile(user_id: str) -> Optional[BuyerProfile]:
    user = await User.get(user_id)
    if not user:
        raise ValueError(f"User with ID {user_id} not found")
    return user.data.buyer_profile


async def user_enable_autonomous_agent(
    user_id: str, criteria: dict, wallet_id: Optional[str] = None
) -> User:
    user = await User.get(user_id)
    if not user:
        raise ValueError(f"User with ID {user_id} not found")
    if not user.data.buyer_profile:
        user.data.buyer_profile = BuyerProfile()
    user.data.buyer_profile.autonomous_agent_enabled = True
    user.data.buyer_profile.autonomous_agent_criteria = criteria
    if wallet_id:
        user.data.buyer_profile.autonomous_agent_wallet_id = wallet_id
    return await User.update(user)


async def user_disable_autonomous_agent(user_id: str) -> User:
    user = await User.get(user_id)
    if not user:
        raise ValueError(f"User with ID {user_id} not found")
    if user.data.buyer_profile:
        user.data.buyer_profile.autonomous_agent_enabled = False
    return await User.update(user)


async def ensure_tigerbeetle_accounts(user_id: str) -> Tuple[int, int]:
    """Ensure TigerBeetle accounts exist for a user, creating them if needed.
    Returns (pending_account_id, settled_account_id).
    """
    user = await User.get(user_id)
    if not user:
        raise ValueError(f"User with ID {user_id} not found")

    if (
        user.data.tigerbeetle_pending_account_id
        and user.data.tigerbeetle_settled_account_id
    ):
        return (
            int(user.data.tigerbeetle_pending_account_id),
            int(user.data.tigerbeetle_settled_account_id),
        )

    from clients.tigerbeetle import create_user_accounts

    loop = asyncio.get_event_loop()
    pending_id, settled_id = await loop.run_in_executor(None, create_user_accounts)

    user.data.tigerbeetle_pending_account_id = str(pending_id)
    user.data.tigerbeetle_settled_account_id = str(settled_id)
    await User.update(user)

    return (pending_id, settled_id)


async def user_get_agent_enabled_buyers() -> List[User]:
    """Find all users where buyer_profile.autonomous_agent_enabled is true."""
    keyspace = User.get_keyspace()
    query = (
        f"SELECT META().id, * FROM {keyspace} "
        f"WHERE buyer_profile.autonomous_agent_enabled = true"
    )
    rows = await keyspace.query(query)
    return [
        User(id=row["id"], data=row.get("users")) for row in rows if row.get("users")
    ]
