import re
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import TenantInviteRecord, TenantMemberRecord, TenantRecord


class TenantRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    # --- Tenant ---

    def create_tenant(self, name: str, plan: str = "starter") -> TenantRecord:
        slug = self._unique_slug(name)
        tenant = TenantRecord(name=name, slug=slug, plan=plan)
        self._session.add(tenant)
        self._session.commit()
        self._session.refresh(tenant)
        return tenant

    def get_tenant(self, tenant_id: int) -> TenantRecord | None:
        return self._session.get(TenantRecord, tenant_id)

    # --- Members ---

    def add_member(self, tenant_id: int, user_id: int, role: str) -> TenantMemberRecord:
        existing = self._session.scalars(
            select(TenantMemberRecord).where(
                TenantMemberRecord.tenant_id == tenant_id,
                TenantMemberRecord.user_id == user_id,
            )
        ).first()
        if existing:
            return existing
        member = TenantMemberRecord(tenant_id=tenant_id, user_id=user_id, role=role)
        self._session.add(member)
        self._session.commit()
        self._session.refresh(member)
        return member

    def list_members_for_user(self, user_id: int) -> list[TenantMemberRecord]:
        return list(
            self._session.scalars(
                select(TenantMemberRecord).where(TenantMemberRecord.user_id == user_id)
            ).all()
        )

    def list_members(self, tenant_id: int) -> list[TenantMemberRecord]:
        return list(
            self._session.scalars(
                select(TenantMemberRecord).where(TenantMemberRecord.tenant_id == tenant_id)
            ).all()
        )

    def get_member(self, tenant_id: int, user_id: int) -> TenantMemberRecord | None:
        return self._session.scalars(
            select(TenantMemberRecord).where(
                TenantMemberRecord.tenant_id == tenant_id,
                TenantMemberRecord.user_id == user_id,
            )
        ).first()

    def remove_member(self, tenant_id: int, user_id: int) -> bool:
        member = self.get_member(tenant_id, user_id)
        if not member:
            return False
        self._session.delete(member)
        self._session.commit()
        return True

    def update_member_role(self, tenant_id: int, user_id: int, role: str) -> TenantMemberRecord | None:
        member = self.get_member(tenant_id, user_id)
        if not member:
            return None
        member.role = role
        self._session.commit()
        return member

    # --- Invites ---

    def create_invite(self, tenant_id: int, email: str, role: str) -> TenantInviteRecord:
        token = secrets.token_urlsafe(32)
        invite = TenantInviteRecord(
            tenant_id=tenant_id,
            email=email.lower(),
            role=role,
            token=token,
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        self._session.add(invite)
        self._session.commit()
        self._session.refresh(invite)
        return invite

    def get_invite_by_token(self, token: str) -> TenantInviteRecord | None:
        return self._session.scalars(
            select(TenantInviteRecord).where(
                TenantInviteRecord.token == token,
                TenantInviteRecord.accepted.is_(False),
                TenantInviteRecord.expires_at > datetime.now(UTC),
            )
        ).first()

    def list_pending_invites(self, tenant_id: int) -> list[TenantInviteRecord]:
        return list(
            self._session.scalars(
                select(TenantInviteRecord).where(
                    TenantInviteRecord.tenant_id == tenant_id,
                    TenantInviteRecord.accepted.is_(False),
                    TenantInviteRecord.expires_at > datetime.now(UTC),
                )
            ).all()
        )

    def accept_invite(self, invite: TenantInviteRecord) -> None:
        invite.accepted = True
        self._session.commit()

    # --- Helpers ---

    def _unique_slug(self, name: str) -> str:
        base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:40] or "workspace"
        slug = base
        attempt = 0
        while self._session.scalars(
            select(TenantRecord).where(TenantRecord.slug == slug)
        ).first():
            attempt += 1
            slug = f"{base}-{attempt}"
        return slug
