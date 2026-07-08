from fastapi import APIRouter, Depends, status, Form
from fastapi.security import OAuth2PasswordRequestForm
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.database.connection import get_database
from app.schemas.pydantic_schemas import UserRegister, UserLogin, Token, UserResponse
from app.services.auth_service import AuthService
from typing import Dict, Any

router = APIRouter(tags=["Authentication"])

@router.post("/api/register", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserRegister, 
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Creates a new system user with Role Based access values.
    """
    return await AuthService.register_user(db, user_in)

@router.post("/api/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Standard OAuth2 password bearer login endpoint. 
    Accepts form-encoded 'username' and 'password' parameters.
    """
    login_schema = UserLogin(username=form_data.username, password=form_data.password)
    return await AuthService.login_user(db, login_schema)

@router.post("/api/login/json", response_model=Token)
async def login_json(
    login_in: UserLogin,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    JSON-based login endpoint. 
    Accepts raw JSON request bodies.
    """
    return await AuthService.login_user(db, login_in)

@router.post("/api/refresh", response_model=Dict[str, str])
async def refresh_token(
    refresh_token: str = Form(...),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Rotates access tokens using a valid refresh token.
    """
    return await AuthService.refresh_access_token(db, refresh_token)
