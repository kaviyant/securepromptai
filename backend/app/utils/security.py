from datetime import datetime, timedelta, timezone
from typing import Optional, Any, Dict
import bcrypt
from jose import JWTError, jwt
from app.config.settings import settings

# JWT Signature algorithms
ALGORITHM = "HS256"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain text password matches its hashed representation.
    """
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    """
    Generates a secure crypt hash of a password using bcrypt.
    """
    # Enforce maximum 72 bytes limit for bcrypt
    pwd_bytes = password.encode('utf-8')
    if len(pwd_bytes) > 72:
        pwd_bytes = pwd_bytes[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')

# 2. Token generation

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Generates a JWT access token for authentication.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Generates a JWT refresh token for obtaining new access tokens.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_REFRESH_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# 3. Token decoding and verification

def decode_token(token: str, secret_key: str) -> Optional[Dict[str, Any]]:
    """
    Decodes and verifies a JWT token. Returns payload or None if invalid.
    """
    try:
        payload = jwt.decode(token, secret_key, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

def verify_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decodes an access token and checks signature integrity.
    """
    payload = decode_token(token, settings.JWT_SECRET_KEY)
    if payload and payload.get("type") == "access":
        return payload
    return None

def verify_refresh_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decodes a refresh token and checks signature integrity.
    """
    payload = decode_token(token, settings.JWT_REFRESH_SECRET_KEY)
    if payload and payload.get("type") == "refresh":
        return payload
    return None
