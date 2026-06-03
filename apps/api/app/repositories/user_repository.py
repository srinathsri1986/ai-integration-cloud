from datetime import UTC, datetime, timedelta
import secrets

from sqlalchemy.orm import Session

from app.db.models import UserRecord


class UserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_email(self, email: str) -> UserRecord | None:
        return self._session.query(UserRecord).filter(UserRecord.email == email.lower()).first()

    def get_by_id(self, user_id: int) -> UserRecord | None:
        return self._session.query(UserRecord).filter(UserRecord.id == user_id).first()

    def get_by_verification_token(self, token: str) -> UserRecord | None:
        return self._session.query(UserRecord).filter(UserRecord.verification_token == token).first()

    def get_by_reset_token(self, token: str) -> UserRecord | None:
        return (
            self._session.query(UserRecord)
            .filter(
                UserRecord.reset_token == token,
                UserRecord.reset_token_expires_at > datetime.now(UTC),
            )
            .first()
        )

    def create(self, email: str, hashed_password: str, role: str) -> UserRecord:
        verification_token = secrets.token_urlsafe(32)
        user = UserRecord(
            email=email.lower(),
            hashed_password=hashed_password,
            role=role,
            is_verified=False,
            verification_token=verification_token,
        )
        self._session.add(user)
        self._session.commit()
        self._session.refresh(user)
        return user

    def verify_email(self, user: UserRecord) -> UserRecord:
        user.is_verified = True
        user.verification_token = None
        self._session.commit()
        self._session.refresh(user)
        return user

    def set_reset_token(self, user: UserRecord) -> str:
        token = secrets.token_urlsafe(32)
        user.reset_token = token
        user.reset_token_expires_at = datetime.now(UTC) + timedelta(hours=1)
        self._session.commit()
        return token

    def update_password(self, user: UserRecord, hashed_password: str) -> UserRecord:
        user.hashed_password = hashed_password
        user.reset_token = None
        user.reset_token_expires_at = None
        self._session.commit()
        self._session.refresh(user)
        return user
