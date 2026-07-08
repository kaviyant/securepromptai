from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.database.connection import get_database
from app.utils.security import verify_access_token
from typing import List, Dict, Any, Optional

# OAuth2 Scheme mapping to register/login token endpoints
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/login", auto_error=False)

async def get_current_user(
    db: AsyncIOMotorDatabase = Depends(get_database),
    token: str = Depends(oauth2_scheme)
) -> Dict[str, Any]:
    """
    Decodes the Bearer token, verifies user existence and status, and returns the DB user document.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not token:
        raise credentials_exception

    payload = verify_access_token(token)
    if not payload:
        raise credentials_exception
        
    username: str = payload.get("sub")
    if not username:
        raise credentials_exception
        
    user = await db.users.find_one({"username": username})
    if not user:
        raise credentials_exception
        
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account"
        )
        
    user["_id"] = str(user["_id"])
    return user

async def get_optional_current_user(
    db: AsyncIOMotorDatabase = Depends(get_database),
    token: Optional[str] = Depends(oauth2_scheme)
) -> Optional[Dict[str, Any]]:
    """
    Optional current user dependency. Returns None instead of throwing 401 if token is missing/invalid.
    """
    if not token:
        return None
    try:
        payload = verify_access_token(token)
        if not payload:
            return None
        username: str = payload.get("sub")
        if not username:
            return None
        user = await db.users.find_one({"username": username})
        if not user or not user.get("is_active", True):
            return None
        user["_id"] = str(user["_id"])
        return user
    except Exception:
        return None

class RoleChecker:
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        """
        Gates access to route by matching the user's role against approved options.
        """
        user_role = current_user.get("role")
        if user_role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation restricted. Required roles: {', '.join(self.allowed_roles)}"
            )
        return current_user

# Predefined role dependencies shortcuts
get_current_admin = RoleChecker(["Admin"])
get_current_employee = RoleChecker(["Admin", "Employee"])
