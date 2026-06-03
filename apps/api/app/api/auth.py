from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.auth import (
    create_access_token,
    create_placeholder_token,
    create_refresh_token,
    decode_refresh_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.core.config import get_settings
from app.core.database import get_session
from app.models.auth import (
    AuthUser,
    ForgotPasswordRequest,
    LegacyLoginRequest,
    LoginRequest,
    LoginResponse,
    MessageResponse,
    RegisterRequest,
    RegisterResponse,
    ResetPasswordRequest,
)
from app.repositories.tenant_repository import TenantRepository
from app.repositories.user_repository import UserRepository
from app.services.email_service import EmailService

router = APIRouter(prefix="/auth", tags=["auth"])


# --- Real auth endpoints ---

@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(
    request: RegisterRequest,
    session: Session = Depends(get_session),
) -> RegisterResponse:
    repo = UserRepository(session)
    if repo.get_by_email(request.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered.")
    hashed = hash_password(request.password)
    user = repo.create(email=request.email, hashed_password=hashed, role=request.role)
    EmailService().send_verification_email(email=user.email, token=user.verification_token or "")
    return RegisterResponse(
        message="Account created. Check your email to verify your address.",
        email=user.email,
    )


@router.get("/verify-email", response_model=MessageResponse)
def verify_email(
    token: str,
    session: Session = Depends(get_session),
) -> MessageResponse:
    user_repo = UserRepository(session)
    user = user_repo.get_by_verification_token(token)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired verification link.")
    user_repo.verify_email(user)

    # Auto-provision a personal workspace for new users
    tenant_repo = TenantRepository(session)
    name = user.email.split("@")[0].replace(".", " ").title() + "'s Workspace"
    tenant = tenant_repo.create_tenant(name=name)
    tenant_repo.add_member(tenant_id=tenant.id, user_id=user.id, role=user.role)

    return MessageResponse(message="Email verified. You can now log in.")


@router.post("/login", response_model=LoginResponse)
def login(
    request: LoginRequest,
    response: Response,
    session: Session = Depends(get_session),
) -> LoginResponse:
    settings = get_settings()
    repo = UserRepository(session)
    user = repo.get_by_email(request.email)
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")
    if not user.is_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email not verified. Check your inbox.")

    # Look up which tenant this user belongs to (first membership)
    tenant_repo = TenantRepository(session)
    members = tenant_repo.list_members_for_user(user_id=user.id)
    tenant_id = members[0].tenant_id if members else None

    access_token = create_access_token(user_id=user.id, email=user.email, role=user.role, tenant_id=tenant_id)
    refresh_token = create_refresh_token(user_id=user.id)

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.environment != "local",
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.environment != "local",
        samesite="lax",
        max_age=settings.refresh_token_expire_days * 86400,
        path="/api/v1/auth/refresh",
    )

    auth_user = AuthUser(userId=str(user.id), email=user.email, role=user.role, tenantId=tenant_id)  # type: ignore[arg-type]
    return LoginResponse(accessToken=access_token, user=auth_user)


@router.post("/refresh", response_model=LoginResponse)
def refresh(
    response: Response,
    refresh_token: str | None = None,
    session: Session = Depends(get_session),
) -> LoginResponse:
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token.")
    settings = get_settings()
    user_id = decode_refresh_token(refresh_token)
    repo = UserRepository(session)
    user = repo.get_by_id(user_id)
    if not user or not user.is_verified:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or unverified.")

    tenant_repo = TenantRepository(session)
    members = tenant_repo.list_members_for_user(user_id=user.id)
    tenant_id = members[0].tenant_id if members else None

    access_token = create_access_token(user_id=user.id, email=user.email, role=user.role, tenant_id=tenant_id)
    new_refresh_token = create_refresh_token(user_id=user.id)

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.environment != "local",
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=settings.environment != "local",
        samesite="lax",
        max_age=settings.refresh_token_expire_days * 86400,
        path="/api/v1/auth/refresh",
    )

    auth_user = AuthUser(userId=str(user.id), email=user.email, role=user.role, tenantId=tenant_id)  # type: ignore[arg-type]
    return LoginResponse(accessToken=access_token, user=auth_user)


@router.post("/logout", response_model=MessageResponse)
def logout(response: Response) -> MessageResponse:
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token", path="/api/v1/auth/refresh")
    return MessageResponse(message="Logged out.")


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(
    request: ForgotPasswordRequest,
    session: Session = Depends(get_session),
) -> MessageResponse:
    repo = UserRepository(session)
    user = repo.get_by_email(request.email)
    if user and user.is_verified:
        token = repo.set_reset_token(user)
        EmailService().send_password_reset_email(email=user.email, token=token)
    # Always return the same message to prevent email enumeration
    return MessageResponse(message="If that email exists, a reset link has been sent.")


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(
    request: ResetPasswordRequest,
    session: Session = Depends(get_session),
) -> MessageResponse:
    repo = UserRepository(session)
    user = repo.get_by_reset_token(request.token)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset link.")
    repo.update_password(user, hash_password(request.password))
    return MessageResponse(message="Password updated. You can now log in.")


@router.get("/me", response_model=AuthUser)
def me(user: AuthUser = Depends(get_current_user)) -> AuthUser:
    return user


# --- Legacy placeholder login (dev/test only) ---

@router.post("/login/placeholder", response_model=LoginResponse, include_in_schema=False)
def login_placeholder(request: LegacyLoginRequest) -> LoginResponse:
    """Local dev / test endpoint. Not for production use."""
    user = AuthUser(userId="local-dev-user", email=request.email, role=request.role)
    return LoginResponse(accessToken=create_placeholder_token(user), user=user)
