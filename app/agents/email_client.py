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


_MOCK_CLIENT = MockEmailClient()


def get_email_client() -> EmailClient:
    return _MOCK_CLIENT


def get_mock_outbox() -> list[SentMessage]:
    return _MOCK_CLIENT.outbox
