import logging
from typing import Any

import resend
from resend.exceptions import ResendError

from core.config import get_settings

logger = logging.getLogger(__name__)


def _mask_email(email: str) -> str:
    if "@" not in email:
        return email[:4] + "****" if email else "<empty>"
    local, domain = email.split("@", 1)
    masked_local = local[:2] + "***" if local else "***"
    return f"{masked_local}@{domain}"


class ResendClient:
    def __init__(
        self,
        api_key: str | None = None,
        from_email: str | None = None,
    ) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.resend_api_key
        self.from_email = from_email or settings.resend_from_email

    def send_alert_email(self, subject: str, body: str, to_email: str) -> bool:
        if not self.api_key or not self.from_email:
            logger.error(
                "Resend configuration incomplete: api_key=%s from_email=%s",
                "set" if self.api_key else "missing",
                _mask_email(self.from_email),
            )
            return False

        payload = {
            "from": self.from_email,
            "to": [to_email],
            "subject": subject,
            "html": f"<pre>{body}</pre>",
        }
        logger.info(
            "Resend request prepared: from=%s to=%s subject=%r",
            _mask_email(self.from_email),
            _mask_email(to_email),
            subject,
        )

        try:
            resend.api_key = self.api_key
            response: Any = resend.Emails.send(payload)
            logger.info("Resend response received: %s", response)
            logger.info("Resend email status: SENT to=%s", _mask_email(to_email))
            return True
        except ResendError as exc:
            logger.error(
                "Resend API error: status=%s type=%s message=%s suggested_action=%s",
                exc.code,
                exc.error_type,
                exc.message,
                exc.suggested_action,
            )
            logger.error("Resend email status: FAILED to=%s", _mask_email(to_email))
            return False
        except Exception as exc:
            logger.error(
                "Resend unexpected error: %s (%s)",
                exc,
                type(exc).__name__,
                exc_info=True,
            )
            logger.error("Resend email status: FAILED to=%s", _mask_email(to_email))
            return False
