# vaultmind_auth_routes.py
# Login and Me endpoints for VaultMind authentication

from fastapi import APIRouter, HTTPException, Depends, Request, status
from pydantic import BaseModel

from core.auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
    TokenData,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

# ─────────────────────────────────────────────────────────────────────────────
# REQUEST / RESPONSE SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    email:    str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type:   str
    user:         dict          # { email, role, name }

# ─────────────────────────────────────────────────────────────────────────────
# POST /api/auth/login
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/login", response_model=LoginResponse)
async def login(request: Request, payload: LoginRequest):
    """
    Authenticate user with email + password.
    Returns a JWT access token on success.
    Rate limited to 5 requests/minute per IP (applied in main.py).
    """
    user = authenticate_user(payload.email, payload.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token({
        "sub":  user["email"],
        "role": user["role"],
        "name": user["name"],
    })

    return {
        "access_token": token,
        "token_type":   "bearer",
        "user": {
            "email": user["email"],
            "role":  user["role"],
            "name":  user["name"],
        },
    }

# ─────────────────────────────────────────────────────────────────────────────
# GET /api/auth/me
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/me")
async def get_me(current_user: TokenData = Depends(get_current_user)):
    """
    Returns current user info decoded from the JWT token.
    Used by frontend on page refresh to verify token is still valid.
    """
    return {
        "email": current_user.email,
        "role":  current_user.role,
        "name":  current_user.name,
    }
