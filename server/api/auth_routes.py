# vaultmind_auth_routes.py
# Login and Me endpoints for VaultMind authentication

from fastapi import APIRouter, HTTPException, Depends, Request, Response, status
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
failed_login_attempts = {}

@router.post("/login", response_model=LoginResponse)
async def login(request: Request, payload: LoginRequest):
    """
    Authenticate user with email + password.
    Returns a JWT access token on success.
    Rate limited to 5 requests/minute per IP (applied in main.py).
    """
    ip = request.client.host if request.client else "unknown"
    if failed_login_attempts.get(ip, 0) >= 5:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Account locked temporarily."
        )

    user = authenticate_user(payload.email, payload.password)

    if not user:
        failed_login_attempts[ip] = failed_login_attempts.get(ip, 0) + 1
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    failed_login_attempts[ip] = 0

    token = create_access_token({
        "sub":  user["email"],
        "role": user["role"],
        "name": user["name"],
    })

    from fastapi.responses import JSONResponse
    response = JSONResponse(content={
        "access_token": token,
        "token_type":   "bearer",
        "user": {
            "email": user["email"],
            "role":  user["role"],
            "name":  user["name"],
        },
    })
    
    # We set the cookie as httponly, secure, samesite=lax
    response.set_cookie(
        key="vm_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=3600  # 1 hour
    )
    
    return response

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("vm_token")
    return {"message": "Logged out successfully"}

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
