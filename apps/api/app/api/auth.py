from fastapi import APIRouter, Depends

from app.core.auth import create_placeholder_token, get_current_user
from app.models.auth import AuthUser, LoginRequest, LoginResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest) -> LoginResponse:
    user = AuthUser(userId="local-dev-user", email=request.email, role=request.role)
    return LoginResponse(accessToken=create_placeholder_token(user), user=user)


@router.get("/me", response_model=AuthUser)
def me(user: AuthUser = Depends(get_current_user)) -> AuthUser:
    return user
