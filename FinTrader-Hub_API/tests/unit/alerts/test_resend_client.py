from unittest.mock import patch

from infrastructure.notifications.email.resend_client import ResendClient


def test_resend_client_returns_false_on_send_error() -> None:
    client = ResendClient(api_key="test-key", from_email="alerts@example.com")

    with patch("infrastructure.notifications.email.resend_client.resend.Emails.send", side_effect=RuntimeError("boom")):
        result = client.send_alert_email(
            subject="Test Alert",
            body="Alert body",
            to_email="user@example.com",
        )

    assert result is False


def test_resend_client_returns_false_when_not_configured() -> None:
    client = ResendClient(api_key="", from_email="")
    result = client.send_alert_email("Subject", "Body", "user@example.com")
    assert result is False
