"""
JWT Authentication System with httpOnly cookies
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Response, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", 480))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", 7))

# Authentication credentials
AUTH_USERNAME = os.getenv("AUTH_USERNAME", "toolstock_admin")
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD", "toolstock2025")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security scheme (opcional, para swagger)
security = HTTPBearer(auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token

    Args:
        data: Data to encode in the token
        expires_delta: Optional expiration time delta

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """
    Create JWT refresh token

    Args:
        data: Data to encode in the token

    Returns:
        Encoded JWT refresh token
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

    return encoded_jwt


def decode_token(token: str) -> dict:
    """
    Decode and verify JWT token

    Args:
        token: JWT token string

    Returns:
        Decoded token payload

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError as e:
        logger.warning(f"Invalid token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
        )


def authenticate_user(username: str, password: str) -> bool:
    """
    Authenticate user with username and password

    Args:
        username: Username
        password: Plain text password

    Returns:
        True if authentication successful
    """
    # En producción, esto debería verificar contra base de datos
    # Por ahora usamos variables de entorno
    if username != AUTH_USERNAME:
        return False

    # Para simplificar, comparamos directamente
    # En producción deberías tener passwords hasheadas en BD
    if password != AUTH_PASSWORD:
        return False

    return True


def get_current_user_from_cookie(request: Request) -> dict:
    """
    Get current user from httpOnly cookie

    Args:
        request: FastAPI request object

    Returns:
        User data from token

    Raises:
        HTTPException: If cookie is missing or invalid
    """
    token = request.cookies.get("access_token")

    if not token:
        logger.warning("No access_token cookie found")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado. Por favor inicia sesión.",
        )

    payload = decode_token(token)

    # Verificar que sea un access token
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        )

    username = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        )

    return {"username": username}


def set_auth_cookies(response: Response, access_token: str, refresh_token: str):
    """
    Set httpOnly cookies for authentication

    Args:
        response: FastAPI response object
        access_token: JWT access token
        refresh_token: JWT refresh token
    """
    # Access token cookie (shorter expiration)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,  # No accesible desde JavaScript
        secure=False,    # True en producción con HTTPS
        samesite="lax",  # Protección CSRF
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # En segundos
        path="/"
    )

    # Refresh token cookie (longer expiration)
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,    # True en producción con HTTPS
        samesite="lax",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,  # En segundos
        path="/auth"     # Solo disponible en rutas /auth/*
    )

    logger.info("Auth cookies set successfully")


def clear_auth_cookies(response: Response):
    """
    Clear authentication cookies (logout)

    Args:
        response: FastAPI response object
    """
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/auth")
    logger.info("Auth cookies cleared")


# Dependency para proteger rutas
async def get_current_user(request: Request) -> dict:
    """
    Dependency to get current authenticated user

    Use this in protected routes:
        @router.get("/protected")
        async def protected_route(current_user: dict = Depends(get_current_user)):
            ...
    """
    return get_current_user_from_cookie(request)


# Dependency opcional (para rutas públicas con info de usuario opcional)
async def get_current_user_optional(request: Request) -> Optional[dict]:
    """
    Optional dependency - returns user if authenticated, None otherwise
    """
    try:
        return get_current_user_from_cookie(request)
    except HTTPException:
        return None
