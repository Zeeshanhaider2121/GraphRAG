"""Authentication endpoints"""
from fastapi import APIRouter
from app.models.request_models import LoginRequest
from app.models.response_models import TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
async def login(request: LoginRequest) -> TokenResponse:
    """Authenticate user and return token"""
    return TokenResponse(access_token="token", token_type="bearer")


@router.post("/logout")
async def logout():
    """Logout user"""
    return {"status": "success", "message": "Logged out successfully"}
