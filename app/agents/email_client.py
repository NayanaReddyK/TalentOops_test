"""Email transport for Communication capability."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Protocol

logger = logging.getLogger("talentops.email")


@dataclass
class SentMessage:
    to: str
    subject: str
    body: str
    message_id: str


class EmailClient(Protocol):
    def send(self, to: str, subject: str, body: str) -> SentMessage:
        ...


@dataclass
class MockEmailClient:
    outbox: list[SentMessage] = field(default_factory=list)

    def send(self, to: str, subject: str, body: str) -> SentMessage:
        msg = SentMessage(
            to=to,
            subject=subject,
            body=body,
            message_id=f"mock-{abs(hash((to, subject))) % 100_000:05d}",
        )
        self.outbox.append(msg)
        logger.info("[mock-email] -> %s | %s", to, subject)
        return msg


class SMTPEmailClient:
    """Production SMTP email transport using app.config settings."""

    def __init__(self):
        from app.config import get_settings
        self.settings = get_settings()

    def send(self, to: str, subject: str, body: str) -> SentMessage:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        import uuid

        from_email = self.settings.SMTP_FROM_EMAIL or self.settings.from_address
        msg = MIMEMultipart()
        msg["From"] = from_email
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        message_id = f"smtp-{uuid.uuid4().hex[:8]}"

        try:
            if not self.settings.SMTP_SERVER:
                raise ValueError("SMTP_SERVER is not configured in environment/settings")

            if self.settings.SMTP_USE_TLS:
                server = smtplib.SMTP(self.settings.SMTP_SERVER, self.settings.SMTP_PORT)
                server.starttls()
            else:
                server = smtplib.SMTP(self.settings.SMTP_SERVER, self.settings.SMTP_PORT)

            if self.settings.SMTP_USERNAME and self.settings.SMTP_PASSWORD:
                server.login(self.settings.SMTP_USERNAME, self.settings.SMTP_PASSWORD)

            server.send_message(msg)
            server.quit()
            logger.info("[smtp-email] Sent email to %s | %s", to, subject)
        except Exception as exc:
            logger.error("Failed to send SMTP email to %s: %s", to, exc)
            raise RuntimeError(f"SMTP email dispatch failed: {exc}") from exc

        return SentMessage(to=to, subject=subject, body=body, message_id=message_id)


_MOCK_CLIENT = MockEmailClient()


def get_email_client() -> EmailClient:
    from app.config import get_settings
    settings = get_settings()
    if settings.email_provider == "smtp":
        return SMTPEmailClient()
    return _MOCK_CLIENT


def get_mock_outbox() -> list[SentMessage]:
    return _MOCK_CLIENT.outbox
