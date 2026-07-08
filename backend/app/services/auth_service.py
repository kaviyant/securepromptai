from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.schemas.pydantic_schemas import UserRegister, UserLogin, Token
from app.utils.security import (
    get_password_hash, 
    verify_password, 
    create_access_token, 
    create_refresh_token,
    verify_refresh_token
)
from typing import Dict, Any, Optional
from bson import ObjectId

class AuthService:
    @staticmethod
    async def register_user(db: AsyncIOMotorDatabase, user_in: UserRegister) -> Dict[str, Any]:
        """
        Creates a new user record in MongoDB, checking for email/username conflicts first.
        """
        # 1. Conflict Check
        existing_email = await db.users.find_one({"email": user_in.email})
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email address already exists."
            )
            
        existing_username = await db.users.find_one({"username": user_in.username})
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This username is already taken."
            )

        # 2. Hash Password and Insert
        hashed_password = get_password_hash(user_in.password)
        user_doc = {
            "username": user_in.username,
            "email": user_in.email,
            "hashed_password": hashed_password,
            "role": user_in.role,
            "department": user_in.department,
            "is_active": True
        }
        
        result = await db.users.insert_one(user_doc)
        user_doc["_id"] = str(result.inserted_id)
        
        # Strip sensitive info
        user_doc.pop("hashed_password")
        return user_doc

    @staticmethod
    async def login_user(db: AsyncIOMotorDatabase, login_in: UserLogin) -> Token:
        """
        Validates login details and issues JWT authentication tokens.
        """
        # 1. Fetch User (allow login by username or email)
        user = await db.users.find_one({
            "$or": [
                {"username": login_in.username},
                {"email": login_in.username}
            ]
        })
        
        if not user or not verify_password(login_in.password, user["hashed_password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is deactivated"
            )

        # 2. Issue JWT Tokens
        token_data = {"sub": user["username"], "role": user["role"]}
        access_token = create_access_token(data=token_data)
        refresh_token = create_refresh_token(data=token_data)
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer"
        )

    @staticmethod
    async def refresh_access_token(db: AsyncIOMotorDatabase, refresh_token: str) -> Dict[str, str]:
        """
        Validates a refresh token and generates a new access token.
        """
        # 1. Decode & Verify
        payload = verify_refresh_token(refresh_token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        username = payload.get("sub")
        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token payload"
            )

        # 2. Verify User Still Exists and is Active
        user = await db.users.find_one({"username": username})
        if not user or not user.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )

        # 3. Generate New Access Token
        token_data = {"sub": user["username"], "role": user["role"]}
        new_access_token = create_access_token(data=token_data)
        
        return {
            "access_token": new_access_token,
            "token_type": "bearer"
        }
