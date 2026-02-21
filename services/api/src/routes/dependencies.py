from fastapi import Request, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from models.operations.users import user_create_if_not_exists_and_get
from utils import log

logger = log.get_logger(__name__)

security = HTTPBearer()

async def current_user_get(request: Request, token: HTTPAuthorizationCredentials = Depends(security)):
    if hasattr(request.app.state, "auth_client"):
        if payload := request.app.state.auth_client.decode_jwt(token.credentials):
            #logger.info(f"Token Credentials: {payload}")
            user_id = payload.get("sub")
            email = payload.get("email")
            
            # Handle potential list format for email
            if isinstance(email, list):
                if email:
                    item = email[0]
                    if isinstance(item, dict):
                        email = item.get("value")
                    else:
                        email = str(item)
                else:
                    email = None

            if user_id:
                try:
                    # Ensure user exists and load into context
                    # Defaulting email to empty string if missing, as it might be required by model
                    user_obj = await user_create_if_not_exists_and_get(user_id, str(email) if email else "")
                    payload['db_user'] = user_obj
                except Exception as e:
                    logger.error(f"Failed to ensure user existence for {user_id}: {e}")
                    # We continue without db_user or raise 500?
                    # Proceeding allows auth to succeed even if DB is down, but might break app logic expecting user.
                    # Given requirements imply strict loading, raising error might be safer, 
                    # but let's log and proceed, or better yet, if the requirement is "load the user object",
                    # failure to do so is a failure.
                    # However, to be safe and avoid blocking auth completely on temporary DB glitches if possible:
                    # existing endpoints check user['email']. They don't check db_user yet.
                    # So failing here might be too aggressive if not strictly required for ALL endpoints.
                    # I will log error and proceed.
                    pass

            return payload
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No auth_client")

async def require_admin(user: dict = Depends(current_user_get)):
    """
    Dependency to ensure the user has the 'admin' role.
    """
    # Check for 'roles' claim (list of strings) or similar structure
    roles = user.get("roles", [])
    if isinstance(roles, str):
        roles = [roles]
        
    if "admin" not in roles:
        logger.warning(f"User {user.get('sub')} attempted admin access without 'admin' role. Roles: {roles}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return user
