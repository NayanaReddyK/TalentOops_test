import asyncio
import smtplib
from email.message import EmailMessage
from app.config import settings
from app.services.database import db
from app.services.logging import get_logger, log_async_function, get_request_id

logger = None
metrics_collector = None
STALE_FLAG = " [STALE: re-run Scorecard?]"


def _dispatch_smtp_email(to: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM_EMAIL or "noreply@talentops.ai"
    msg["To"] = to
    msg.set_content(body)

    with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT, timeout=10) as server:
        if settings.SMTP_USE_TLS:
            server.starttls()
        if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.send_message(msg)


@log_async_function("email_service")
async def send_email(to: str, subject: str, body: str) -> dict:
    """Send an email using real SMTP if configured and record in database audit.

    Args:
        to: Recipient email address
        subject: Email subject line
        body: Email body content

    Returns:
        Database record of the email sent
    """
    # Lazy initialization to avoid circular imports
    global logger, metrics_collector
    if logger is None:
        from app.services.logging import get_metrics
        logger = get_logger(__name__)
        metrics_collector = get_metrics()

    try:
        logger.info(
            "Preparing to send email",
            extra={
                "to": to,
                "subject": subject,
                "request_id": get_request_id()
            }
        )

        smtp_status = "sent"
        if settings.SMTP_SERVER and not settings.is_offline_mode:
            try:
                await asyncio.to_thread(_dispatch_smtp_email, to, subject, body)
                logger.info("Real SMTP email dispatched", extra={"to": to, "request_id": get_request_id()})
            except Exception as smtp_err:
                smtp_status = "delivery_error"
                logger.error(
                    "SMTP delivery failed, falling back to db audit record",
                    exc_info=True,
                    extra={"to": to, "error_type": type(smtp_err).__name__, "request_id": get_request_id()}
                )

        result = await db.insert("comms", {
            "to": to,
            "subject": subject,
            "body": body,
            "status": smtp_status
        })

        logger.info(
            "Email successfully recorded",
            extra={
                "to": to,
                "status": smtp_status,
                "request_id": get_request_id()
            }
        )

        return result
    except Exception as e:
        logger.error(
            "Failed to send email",
            exc_info=True,
            extra={
                "to": to,
                "subject": subject,
                "error_type": type(e).__name__,
                "request_id": get_request_id()
            }
        )
        if metrics_collector:
            metrics_collector.increment_error_count("email", "send")
        raise


@log_async_function("email_service")
async def _is_stale(role_id: str) -> bool:
    """Check if scorecards are stale compared to interviews.

    Args:
        role_id: Role identifier

    Returns:
        True if scorecards are stale, False otherwise
    """
    # Lazy initialization
    global logger
    if logger is None:
        from app.services.logging import get_logger
        logger = get_logger(__name__)

    try:
        logger.debug(
            "Checking scorecard staleness",
            extra={
                "role_id": role_id,
                "request_id": get_request_id()
            }
        )

        interviews = await db.query("interviews", role_id=role_id)
        interview_cids = {iv.get("candidate_id") for iv in interviews}
        scorecards = await db.query("scorecards")
        role_scorecards = [s for s in scorecards if s.get("candidate_id") in interview_cids]

        if not interviews:
            return False

        if not role_scorecards:
            return True

        # Check if any interviews have higher sequence numbers
        return max(r["_seq"] for r in interviews) > max(r["_seq"] for r in role_scorecards)
    except Exception as e:
        logger.error(
            "Failed to check scorecard staleness",
            exc_info=True,
            extra={
                "role_id": role_id,
                "error_type": type(e).__name__,
                "request_id": get_request_id()
            }
        )
        raise


@log_async_function("email_service")
async def handle_incoming_email(payload: dict) -> dict:
    """Process incoming email and send pipeline state update.

    Args:
        payload: Email payload with role_id, from, subject fields

    Returns:
        Email status result
    """
    # Lazy initialization
    global logger, metrics_collector
    if logger is None:
        from app.services.logging import get_metrics
        logger = get_logger(__name__)
        metrics_collector = get_metrics()

    try:
        role_id = payload.get("role_id", "")

        logger.info(
            "Handling incoming email",
            extra={
                "role_id": role_id,
                "from": payload.get("from"),
                "subject": payload.get("subject"),
                "request_id": get_request_id()
            }
        )

        candidates = await db.query("candidates", role_id=role_id)
        interview_cids = {iv.get("candidate_id") for iv in await db.query("interviews", role_id=role_id)}
        scorecards = [s for s in await db.query("scorecards") if s.get("candidate_id") in interview_cids]
        names = ", ".join(c.get("name", "?") for c in candidates) or "none yet"

        body = (
            f"Current pipeline state — candidates: {len(candidates)} ({names}); "
            f"scorecards complete: {len(scorecards)}."
        )

        if await _is_stale(role_id):
            body += STALE_FLAG

        result = await send_email(
            payload["from"],
            "Re: " + payload.get("subject", ""),
            body
        )

        logger.info(
            "Email update sent successfully",
            extra={
                "role_id": role_id,
                "candidates_count": len(candidates),
                "scorecards_complete": len(scorecards),
                "is_stale": await _is_stale(role_id),
                "request_id": get_request_id()
            }
        )

        return result
    except Exception as e:
        logger.error(
            "Failed to handle incoming email",
            exc_info=True,
            extra={
                "role_id": payload.get("role_id"),
                "error_type": type(e).__name__,
                "request_id": get_request_id()
            }
        )
        if metrics_collector:
            metrics_collector.increment_error_count("email", "handle")
        raise
