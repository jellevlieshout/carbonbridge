from typing import Dict, Any
from models.entities.couchbase.users import User, UserData

async def user_get_data_for_frontend(user_id: str) -> Dict[str, Any]:
    """
    Retrieves user information.
    
    Args:
        user_id (str): The ID of the user.
    """
    user = await User.get(user_id)
    
    if not user:
        raise ValueError(f"User with ID {user_id} not found")

    return {
        "user": user.data.model_dump()
    }


async def user_create_if_not_exists_and_get(user_id: str, email: str) -> User:
    """
    Checks if a user exists by user_id. If not, creates the user and returns the User object.
    Uses user_id as the document key.
    """
    existing_user = await User.get(user_id)
    if existing_user:
        return existing_user

    new_user_data = UserData(email=email)
    return await User.create(new_user_data, key=user_id, user_id=user_id)
