"""Email transport for the Communication capability (Gmail API).

``MockEmailClient`` records sent messages in-process so the whole comms flow —
invites, rejections, digests, Q&A replies — works with no OAuth. Every sent
message is also mirrored to the ``events`` audit log by the caller.
``GmailClient`` is the real path, built lazily from OAuth2 credentials.
"""
from __future__ import annotations

import base64
import logging
from dataclasses import dataclass, field
from email.mime.text import MIMEText
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
    """Records messages in an in-process outbox — no network, no OAuth."""

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


class GmailClient:
    """Real Gmail send via the Google API using OAuth2 token.json."""

    def __init__(self, token_path: str, from_address: str):
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        creds = Credentials.from_authorized_user_file(
            token_path, ["https://www.googleapis.com/auth/gmail.send"]
        )
        # Auto-refresh if expired
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
        self._svc = build("gmail", "v1", credentials=creds)
        self._from = from_address

    def send(self, to: str, subject: str, body: str) -> SentMessage:
        mime = MIMEText(body, "html")
        mime["to"] = to
        mime["from"] = self._from
        mime["subject"] = subject
        raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()
        sent = self._svc.users().messages().send(userId="me", body={"raw": raw}).execute()
        logger.info("[gmail] Sent to %s | %s | ID: %s", to, subject, sent["id"])
        return SentMessage(to=to, subject=subject, body=body, message_id=sent["id"])


# Singleton mock outbox so digests / tests can inspect what was "sent".
_MOCK_CLIENT = MockEmailClient()


def get_email_client() -> EmailClient:
    from app.config import get_settings

    settings = get_settings()
    if settings.email_provider == "mock":
        return _MOCK_CLIENT

    # Graceful fallback if token.json doesn't exist yet
    import os
    token_path = settings.google_token_path
    if not os.path.exists(token_path):
        logger.warning(
            "Email set to 'gmail' but %s not found — falling back to MockEmailClient. "
            "Run: python scripts/auth_google.py",
            token_path,
        )
        return _MOCK_CLIENT

    return GmailClient(token_path, settings.from_address)


def get_mock_outbox() -> list[SentMessage]:
    """Expose the mock outbox (for the demo / digest / tests)."""
    return _MOCK_CLIENT.outbox
