import os
import logging
from datetime import datetime, timedelta
from typing import Optional
from dotenv import load_dotenv
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx

from app.database import get_db, User

load_dotenv()

logger = logging.getLogger(__name__)

# Configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_DAYS = 7

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

security = HTTPBearer(auto_error=False)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(days=JWT_EXPIRATION_DAYS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


async def get_google_tokens(code: str, redirect_uri: str) -> dict:
    """Exchange authorization code for tokens"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        if response.status_code != 200:
            error_body = response.text
            logger.error(f"Google token exchange failed ({response.status_code}): {error_body}")
            logger.error(f"redirect_uri used: {redirect_uri}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to get tokens from Google: {error_body}"
            )
        return response.json()


async def get_google_user_info(access_token: str) -> dict:
    """Get user info from Google"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get user info from Google"
            )
        return response.json()


async def get_or_create_user(db: AsyncSession, google_user: dict) -> User:
    """Get existing user or create new one from Google data"""
    google_id = str(google_user.get("id"))
    
    # Try to find existing user
    result = await db.execute(
        select(User).where(User.google_id == google_id)
    )
    user = result.scalar_one_or_none()
    
    if user:
        # Update user info if changed
        user.email = google_user.get("email")
        user.name = google_user.get("name")
        user.avatar_url = google_user.get("picture")
        await db.commit()
        return user
    
    # Create new user
    user = User(
        google_id=google_id,
        email=google_user.get("email"),
        name=google_user.get("name"),
        avatar_url=google_user.get("picture"),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Get current user from JWT token (optional auth)"""
    if not credentials:
        return None
    
    payload = decode_token(credentials.credentials)
    if not payload:
        return None
    
    user_id = payload.get("sub")
    if not user_id:
        return None
    
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def get_current_user_required(
    user: Optional[User] = Depends(get_current_user)
) -> User:
    """Get current user (required - raises 401 if not authenticated)"""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_google_oauth_url(redirect_uri: str) -> str:
    """Generate Google OAuth URL"""
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"https://accounts.google.com/o/oauth2/v2/auth?{query}"

