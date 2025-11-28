"""
Authentication endpoints - Login, Logout, Refresh Token
"""
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from pydantic import BaseModel, Field
from app.auth import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    set_auth_cookies,
    clear_auth_cookies,
    decode_token,
    get_current_user
)
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    """Login request schema"""
    username: str = Field(..., min_length=3, description="Username")
    password: str = Field(..., min_length=4, description="Password")


class LoginResponse(BaseModel):
    """Login response schema"""
    message: str
    username: str
    token_type: str = "Bearer"


@router.post("/login", response_model=LoginResponse)
async def login(credentials: LoginRequest, response: Response):
    """
    Login endpoint - Returns JWT tokens in httpOnly cookies

    **Como usar:**

    ```javascript
    // Frontend (Axios)
    const response = await axios.post('http://127.0.0.1:8000/auth/login', {
        username: 'toolstock_admin',
        password: 'toolstock2025'
    }, {
        withCredentials: true  // IMPORTANTE: Permite cookies
    });
    ```

    **Respuesta:**
    - Las cookies se envían automáticamente
    - Las siguientes requests incluirán las cookies automáticamente
    """
    logger.info(f"Login attempt for user: {credentials.username}")

    # Authenticate user
    if not authenticate_user(credentials.username, credentials.password):
        logger.warning(f"Failed login attempt for: {credentials.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
        )

    # Create tokens
    access_token = create_access_token(data={"sub": credentials.username})
    refresh_token = create_refresh_token(data={"sub": credentials.username})

    # Set httpOnly cookies
    set_auth_cookies(response, access_token, refresh_token)

    logger.info(f"User {credentials.username} logged in successfully")

    return LoginResponse(
        message="Inicio de sesión exitoso",
        username=credentials.username
    )


@router.post("/logout")
async def logout(
    response: Response,
    current_user: dict = Depends(get_current_user)
):
    """
    Logout endpoint - Clears authentication cookies

    **Como usar:**

    ```javascript
    // Frontend (Axios)
    const response = await axios.post('http://127.0.0.1:8000/auth/logout', {}, {
        withCredentials: true
    });
    ```
    """
    logger.info(f"User {current_user['username']} logging out")

    # Clear cookies
    clear_auth_cookies(response)

    return {
        "message": "Sesión cerrada exitosamente"
    }


@router.post("/refresh")
async def refresh_token(request: Request, response: Response):
    """
    Refresh access token using refresh token

    **Como usar:**

    Este endpoint se llama automáticamente cuando el access token expira.
    El frontend debe detectar error 401 y llamar a /auth/refresh.

    ```javascript
    // Frontend (Axios con interceptor)
    axios.interceptors.response.use(
        response => response,
        async error => {
            if (error.response?.status === 401) {
                await axios.post('http://127.0.0.1:8000/auth/refresh', {}, {
                    withCredentials: true
                });
                // Reintentar request original
                return axios.request(error.config);
            }
            return Promise.reject(error);
        }
    );
    ```
    """
    # Get refresh token from cookie
    refresh_token_value = request.cookies.get("refresh_token")

    if not refresh_token_value:
        logger.warning("Refresh token not found")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No hay token de actualización. Por favor inicia sesión nuevamente.",
        )

    try:
        # Decode refresh token
        payload = decode_token(refresh_token_value)

        # Verify it's a refresh token
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido",
            )

        username = payload.get("sub")

        # Create new access token
        new_access_token = create_access_token(data={"sub": username})

        # Set new access token cookie (keep refresh token)
        response.set_cookie(
            key="access_token",
            value=new_access_token,
            httponly=True,
            secure=False,
            samesite="lax",
            max_age=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", 480)) * 60,
            path="/"
        )

        logger.info(f"Access token refreshed for user: {username}")

        return {
            "message": "Token actualizado exitosamente",
            "username": username
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Error al actualizar el token. Por favor inicia sesión nuevamente.",
        )


@router.get("/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """
    Get current authenticated user information

    **Como usar:**

    ```javascript
    // Frontend (Axios)
    const response = await axios.get('http://127.0.0.1:8000/auth/me', {
        withCredentials: true
    });
    console.log(response.data);  // { username: "toolstock_admin" }
    ```
    """
    return {
        "username": current_user["username"],
        "authenticated": True
    }


@router.get("/check")
async def check_auth_status(request: Request):
    """
    Check if user is authenticated (no exception thrown)

    Returns authentication status without requiring authentication.

    **Como usar:**

    ```javascript
    // Frontend - Check if user is logged in
    const response = await axios.get('http://127.0.0.1:8000/auth/check', {
        withCredentials: true
    });
    if (response.data.authenticated) {
        console.log('User is logged in:', response.data.username);
    }
    ```
    """
    try:
        token = request.cookies.get("access_token")
        if not token:
            return {
                "authenticated": False,
                "username": None
            }

        payload = decode_token(token)
        username = payload.get("sub")

        return {
            "authenticated": True,
            "username": username
        }
    except:
        return {
            "authenticated": False,
            "username": None
        }


# Import needed for refresh endpoint
import os
