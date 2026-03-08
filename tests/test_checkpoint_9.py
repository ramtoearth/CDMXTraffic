"""
Task 9 checkpoint: integration-style unit tests (all mocked, no real AWS calls).

Verifies:
- Successful subscription triggers welcome email Lambda invoke
- Welcome email Lambda failure does NOT block subscription success
- Reactivation also triggers welcome email
"""
import json
from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from src.shared.models import Subscriber, SubscribeResponse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_subscriber(**overrides) -> Subscriber:
    defaults = dict(
        subscriber_id=str(uuid4()),
        email="test@example.com",
        name="Test User",
        frequency="daily",
        subscribed_at=datetime.now(),
        active=True,
        unsubscribe_token=str(uuid4()),
    )
    defaults.update(overrides)
    return Subscriber(**defaults)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestFullSubscriptionTriggersWelcomeEmail:
    """New subscription → save succeeds → welcome email Lambda invoked."""

    def test_full_subscription_triggers_welcome_email(self, monkeypatch):
        subscriber = _make_subscriber()

        monkeypatch.setenv("SUBSCRIBERS_TABLE", "test-table")
        monkeypatch.setenv("SEND_EMAIL_FUNCTION_NAME", "dev-cdmx-traffic-send-email")
        monkeypatch.setenv("LANDING_PAGE_URL", "https://example.com")

        mock_lambda_client = MagicMock()
        mock_lambda_client.invoke.return_value = {"StatusCode": 202}

        with patch(
            "src.subscribe.subscription_logic.get_subscriber_by_email",
            return_value=None,
        ), patch(
            "src.subscribe.subscription_logic.save_subscriber_to_db",
            return_value=True,
        ), patch(
            "src.subscribe.subscription_logic.boto3.client",
            return_value=mock_lambda_client,
        ), patch(
            "src.subscribe.subscription_logic.Subscriber",
            return_value=subscriber,
        ):
            from src.subscribe.subscription_logic import validate_and_save_subscriber

            result = validate_and_save_subscriber(
                email="test@example.com",
                frequency="daily",
                name="Test User",
            )

        assert result.success is True
        mock_lambda_client.invoke.assert_called_once()
        call_kwargs = mock_lambda_client.invoke.call_args[1]
        assert call_kwargs["FunctionName"] == "dev-cdmx-traffic-send-email"
        payload = json.loads(call_kwargs["Payload"])
        assert payload["to_email"] == subscriber.email
        assert payload["newsletter_type"] == "welcome"


class TestWelcomeEmailFailureDoesNotBlockSubscription:
    """Lambda.invoke raises → subscription still returns success."""

    def test_welcome_email_failure_does_not_block_subscription(self, monkeypatch):
        subscriber = _make_subscriber()

        monkeypatch.setenv("SUBSCRIBERS_TABLE", "test-table")
        monkeypatch.setenv("SEND_EMAIL_FUNCTION_NAME", "dev-cdmx-traffic-send-email")
        monkeypatch.setenv("LANDING_PAGE_URL", "https://example.com")

        mock_lambda_client = MagicMock()
        mock_lambda_client.invoke.side_effect = Exception("Lambda unavailable")

        with patch(
            "src.subscribe.subscription_logic.get_subscriber_by_email",
            return_value=None,
        ), patch(
            "src.subscribe.subscription_logic.save_subscriber_to_db",
            return_value=True,
        ), patch(
            "src.subscribe.subscription_logic.boto3.client",
            return_value=mock_lambda_client,
        ), patch(
            "src.subscribe.subscription_logic.Subscriber",
            return_value=subscriber,
        ):
            from src.subscribe.subscription_logic import validate_and_save_subscriber

            result = validate_and_save_subscriber(
                email="test@example.com",
                frequency="daily",
                name="Test User",
            )

        # Subscription must succeed despite email Lambda failure
        assert result.success is True


class TestReactivationAlsoTriggersWelcomeEmail:
    """Reactivated subscriber also gets welcome email."""

    def test_reactivation_also_triggers_welcome_email(self, monkeypatch):
        existing = _make_subscriber(active=False)

        monkeypatch.setenv("SUBSCRIBERS_TABLE", "test-table")
        monkeypatch.setenv("SEND_EMAIL_FUNCTION_NAME", "dev-cdmx-traffic-send-email")
        monkeypatch.setenv("LANDING_PAGE_URL", "https://example.com")

        mock_lambda_client = MagicMock()
        mock_lambda_client.invoke.return_value = {"StatusCode": 202}

        with patch(
            "src.subscribe.subscription_logic.get_subscriber_by_email",
            return_value=existing,
        ), patch(
            "src.subscribe.subscription_logic.save_subscriber_to_db",
            return_value=True,
        ), patch(
            "src.subscribe.subscription_logic.boto3.client",
            return_value=mock_lambda_client,
        ):
            from src.subscribe.subscription_logic import validate_and_save_subscriber

            result = validate_and_save_subscriber(
                email=existing.email,
                frequency="weekly",
                name=existing.name,
            )

        assert result.success is True
        assert result.message == "Subscription reactivated"
        mock_lambda_client.invoke.assert_called_once()
        call_kwargs = mock_lambda_client.invoke.call_args[1]
        payload = json.loads(call_kwargs["Payload"])
        assert payload["newsletter_type"] == "welcome"
