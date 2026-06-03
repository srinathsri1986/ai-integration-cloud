import logging

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._resend_client = None
        if self._settings.resend_api_key:
            import resend
            resend.api_key = self._settings.resend_api_key
            self._resend_client = resend

    def send_verification_email(self, email: str, token: str) -> None:
        verify_url = f"{self._settings.app_base_url}/verify-email?token={token}"
        subject = "Verify your AI Integration Cloud account"
        html = f"""
        <h2>Welcome to AI Integration Cloud</h2>
        <p>Click the link below to verify your email address:</p>
        <p><a href="{verify_url}">{verify_url}</a></p>
        <p>This link expires in 24 hours.</p>
        """
        self._send(to=email, subject=subject, html=html)

    def send_password_reset_email(self, email: str, token: str) -> None:
        reset_url = f"{self._settings.app_base_url}/reset-password?token={token}"
        subject = "Reset your AI Integration Cloud password"
        html = f"""
        <h2>Password Reset</h2>
        <p>Click the link below to reset your password:</p>
        <p><a href="{reset_url}">{reset_url}</a></p>
        <p>This link expires in 1 hour. If you did not request a reset, ignore this email.</p>
        """
        self._send(to=email, subject=subject, html=html)

    def send_invite_email(self, email: str, tenant_name: str, role: str, token: str) -> None:
        accept_url = f"{self._settings.app_base_url}/accept-invite?token={token}"
        subject = f"You're invited to join {tenant_name} on AI Integration Cloud"
        html = f"""
        <h2>You're invited!</h2>
        <p>You've been invited to join <strong>{tenant_name}</strong> as <strong>{role}</strong>.</p>
        <p>Click the link below to accept the invitation:</p>
        <p><a href="{accept_url}">{accept_url}</a></p>
        <p>This invite expires in 7 days.</p>
        """
        self._send(to=email, subject=subject, html=html)

    def _send(self, to: str, subject: str, html: str) -> None:
        if self._resend_client:
            try:
                self._resend_client.Emails.send({
                    "from": "AI Integration Cloud <noreply@aiintegrationcloud.com>",
                    "to": [to],
                    "subject": subject,
                    "html": html,
                })
                logger.info("Email sent via Resend.", extra={"to": to, "subject": subject})
            except Exception:
                logger.exception("Failed to send email via Resend.", extra={"to": to})
        else:
            logger.info(
                "Email (mock — set RESEND_API_KEY to send real emails).",
                extra={"to": to, "subject": subject, "html": html},
            )
