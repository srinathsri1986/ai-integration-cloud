from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, require_permissions
from app.core.database import get_session
from app.models.auth import AuthUser, UserRole
from app.repositories.tenant_repository import TenantRepository
from app.repositories.user_repository import UserRepository
from app.services.email_service import EmailService

router = APIRouter(prefix="/tenants", tags=["tenants"])


# --- Response models ---

class TenantResponse(BaseModel):
    id: int
    name: str
    slug: str
    plan: str


class TenantMemberResponse(BaseModel):
    userId: int
    email: str
    role: str


class InviteRequest(BaseModel):
    email: EmailStr
    role: UserRole = "Developer"


class InviteResponse(BaseModel):
    message: str
    email: str
    role: str


class PendingInviteResponse(BaseModel):
    id: int
    email: str
    role: str


class AcceptInviteRequest(BaseModel):
    token: str


class UpdateMemberRoleRequest(BaseModel):
    role: UserRole


class MessageResponse(BaseModel):
    message: str


# --- Helpers ---

def _require_tenant(user: AuthUser) -> int:
    if user.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No active workspace. Log in with a verified account.",
        )
    return user.tenant_id


# --- Endpoints ---

@router.get("/me", response_model=TenantResponse)
def get_current_tenant(
    session: Session = Depends(get_session),
    user: AuthUser = Depends(get_current_user),
) -> TenantResponse:
    tenant_id = _require_tenant(user)
    tenant = TenantRepository(session).get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found.")
    return TenantResponse(id=tenant.id, name=tenant.name, slug=tenant.slug, plan=tenant.plan)


@router.get("/me/members", response_model=list[TenantMemberResponse])
def list_members(
    session: Session = Depends(get_session),
    user: AuthUser = Depends(require_permissions("connector:admin")),
) -> list[TenantMemberResponse]:
    tenant_id = _require_tenant(user)
    repo = TenantRepository(session)
    user_repo = UserRepository(session)
    members = repo.list_members(tenant_id)
    result = []
    for member in members:
        u = user_repo.get_by_id(member.user_id)
        if u:
            result.append(TenantMemberResponse(userId=u.id, email=u.email, role=member.role))
    return result


@router.post("/me/members/invite", response_model=InviteResponse, status_code=status.HTTP_201_CREATED)
def invite_member(
    request: InviteRequest,
    session: Session = Depends(get_session),
    user: AuthUser = Depends(require_permissions("connector:admin")),
) -> InviteResponse:
    tenant_id = _require_tenant(user)
    repo = TenantRepository(session)
    tenant = repo.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found.")

    invite = repo.create_invite(tenant_id=tenant_id, email=request.email, role=request.role)
    EmailService().send_invite_email(
        email=invite.email,
        tenant_name=tenant.name,
        role=invite.role,
        token=invite.token,
    )
    return InviteResponse(
        message="Invite sent.",
        email=invite.email,
        role=invite.role,
    )


@router.get("/me/members/invites", response_model=list[PendingInviteResponse])
def list_pending_invites(
    session: Session = Depends(get_session),
    user: AuthUser = Depends(require_permissions("connector:admin")),
) -> list[PendingInviteResponse]:
    tenant_id = _require_tenant(user)
    invites = TenantRepository(session).list_pending_invites(tenant_id)
    return [PendingInviteResponse(id=inv.id, email=inv.email, role=inv.role) for inv in invites]


@router.post("/accept-invite", response_model=MessageResponse)
def accept_invite(
    request: AcceptInviteRequest,
    session: Session = Depends(get_session),
    user: AuthUser = Depends(get_current_user),
) -> MessageResponse:
    if user.user_id == "local-dev-user":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Must be logged in.")
    repo = TenantRepository(session)
    invite = repo.get_invite_by_token(request.token)
    if not invite:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired invite.")

    user_repo = UserRepository(session)
    real_user = user_repo.get_by_id(int(user.user_id))
    if not real_user or real_user.email.lower() != invite.email.lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This invite was sent to a different email address.",
        )

    repo.add_member(tenant_id=invite.tenant_id, user_id=real_user.id, role=invite.role)
    repo.accept_invite(invite)
    return MessageResponse(message="Joined workspace.")


@router.delete("/me/members/{user_id}", response_model=MessageResponse)
def remove_member(
    user_id: int,
    session: Session = Depends(get_session),
    user: AuthUser = Depends(require_permissions("connector:admin")),
) -> MessageResponse:
    tenant_id = _require_tenant(user)
    if str(user_id) == user.user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot remove yourself.")
    removed = TenantRepository(session).remove_member(tenant_id=tenant_id, user_id=user_id)
    if not removed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found.")
    return MessageResponse(message="Member removed.")


@router.put("/me/members/{user_id}/role", response_model=TenantMemberResponse)
def update_member_role(
    user_id: int,
    request: UpdateMemberRoleRequest,
    session: Session = Depends(get_session),
    user: AuthUser = Depends(require_permissions("connector:admin")),
) -> TenantMemberResponse:
    tenant_id = _require_tenant(user)
    repo = TenantRepository(session)
    member = repo.update_member_role(tenant_id=tenant_id, user_id=user_id, role=request.role)
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found.")
    user_repo = UserRepository(session)
    u = user_repo.get_by_id(user_id)
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return TenantMemberResponse(userId=u.id, email=u.email, role=member.role)
