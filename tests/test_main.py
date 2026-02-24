"""
Tests for the STC Hackathon API.

Run with:
    pytest tests/test_main.py -v
"""

import json
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.v1.deps import get_current_clerk_user
from app.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_image_file(filename="photo.jpg", content_type="image/jpeg", size=256):
    """Return a files tuple for TestClient multipart upload."""
    return ("file", (filename, BytesIO(b"\xff\xd8\xff" + b"\x00" * size), content_type))


def _mock_openai_response(recipe: dict):
    """Build a minimal mock that looks like an OpenAI ChatCompletion response."""
    message = MagicMock()
    message.content = json.dumps(recipe)
    choice = MagicMock()
    choice.message = message
    completion = MagicMock()
    completion.choices = [choice]
    return completion


@pytest.fixture(autouse=True)
def _reset_dependency_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to my FastAPI application!"}


# ---------------------------------------------------------------------------
# POST /api/v1/upload-image/
# ---------------------------------------------------------------------------

def test_upload_image_rejects_non_image():
    """PDF and other non-image types must be rejected with 400."""
    file = ("file", ("doc.pdf", BytesIO(b"%PDF-1.4"), "application/pdf"))
    response = client.post("/api/v1/upload-image/", files=[file])
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_upload_image_rejects_oversized_file():
    """Files larger than 10 MB must be rejected with 413."""
    big_content = b"\xff\xd8\xff" + b"\x00" * (10 * 1024 * 1024 + 1)
    file = ("file", ("big.jpg", BytesIO(big_content), "image/jpeg"))
    response = client.post("/api/v1/upload-image/", files=[file])
    assert response.status_code == 413
    assert "File too large" in response.json()["detail"]


@patch("app.api.v1.endpoints.settings")
def test_upload_image_missing_api_key(mock_settings):
    """Missing OpenAI API key must return 500 if using default OpenAI URL."""
    mock_settings.openai_api_key = ""
    mock_settings.model_url = "https://api.openai.com/v1"
    response = client.post("/api/v1/upload-image/", files=[_make_image_file()])
    assert response.status_code == 500
    assert "not configured" in response.json()["detail"]


@patch("app.api.v1.endpoints.AsyncOpenAI")
@patch("app.api.v1.endpoints.settings")
def test_upload_image_success(mock_settings, mock_openai_cls):
    """Happy path: image is forwarded to OpenAI and the JSON recipe is returned."""
    mock_settings.openai_api_key = "sk-test-key"

    recipe = {
        "name": "Tomato Salad",
        "ingredients": ["3 tomatoes", "1 cucumber"],
        "time": 10,
        "steps": ["Chop vegetables.", "Mix together.", "Serve."],
    }

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_mock_openai_response(recipe)
    )
    mock_openai_cls.return_value = mock_client

    response = client.post("/api/v1/upload-image/", files=[_make_image_file()])

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Tomato Salad"
    assert data["time"] == 10
    assert isinstance(data["ingredients"], list)
    assert isinstance(data["steps"], list)


@patch("app.api.v1.endpoints.AsyncOpenAI")
@patch("app.api.v1.endpoints.settings")
def test_upload_image_openai_error(mock_settings, mock_openai_cls):
    """OpenAI API errors must be surfaced as 502."""
    mock_settings.openai_api_key = "sk-test-key"

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=Exception("connection refused")
    )
    mock_openai_cls.return_value = mock_client

    response = client.post("/api/v1/upload-image/", files=[_make_image_file()])

    assert response.status_code == 502
    assert "OpenAI API error" in response.json()["detail"]


@patch("app.api.v1.endpoints.AsyncOpenAI")
@patch("app.api.v1.endpoints.settings")
def test_upload_image_invalid_json_from_openai(mock_settings, mock_openai_cls):
    """If OpenAI returns non-JSON, the endpoint must return 502."""
    mock_settings.openai_api_key = "sk-test-key"

    message = MagicMock()
    message.content = "Sorry, I cannot help with that."
    choice = MagicMock()
    choice.message = message
    completion = MagicMock()
    completion.choices = [choice]

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=completion)
    mock_openai_cls.return_value = mock_client

    response = client.post("/api/v1/upload-image/", files=[_make_image_file()])

    assert response.status_code == 502
    assert "invalid JSON" in response.json()["detail"]


@patch("app.api.v1.endpoints.AsyncOpenAI")
@patch("app.api.v1.endpoints.settings")
def test_upload_image_markdown_json_response(mock_settings, mock_openai_cls):
    """If OpenAI returns JSON wrapped in markdown backticks, it should be parsed correctly."""
    mock_settings.openai_api_key = "sk-test-key"

    raw_content = "```json\n{\"name\": \"Salad\", \"ingredients\": [], \"time\": 5, \"steps\": []}\n```"
    message = MagicMock()
    message.content = raw_content
    choice = MagicMock()
    choice.message = message
    completion = MagicMock()
    completion.choices = [choice]

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=completion)
    mock_openai_cls.return_value = mock_client

    response = client.post("/api/v1/upload-image/", files=[_make_image_file()])

    assert response.status_code == 200
    assert response.json()["name"] == "Salad"


@patch("app.api.v1.endpoints.AsyncOpenAI")
@patch("app.api.v1.endpoints.settings")
def test_upload_image_fallback_json_parsing(mock_settings, mock_openai_cls):
    """If OpenAI returns JSON with text around it (no backticks), it should still be parsed."""
    mock_settings.openai_api_key = "sk-test-key"

    raw_content = "Sure, here's your recipe: {\"name\": \"Soup\", \"ingredients\": [], \"time\": 15, \"steps\": []} Hope you like it!"
    message = MagicMock()
    message.content = raw_content
    choice = MagicMock()
    choice.message = message
    completion = MagicMock()
    completion.choices = [choice]

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=completion)
    mock_openai_cls.return_value = mock_client

    response = client.post("/api/v1/upload-image/", files=[_make_image_file()])

    assert response.status_code == 200
    assert response.json()["name"] == "Soup"


@pytest.mark.parametrize("content_type", ["image/jpeg", "image/png", "image/webp", "image/gif"])
@patch("app.api.v1.endpoints.AsyncOpenAI")
@patch("app.api.v1.endpoints.settings")
def test_upload_image_all_allowed_types(mock_settings, mock_openai_cls, content_type):
    """All four allowed image MIME types must be accepted."""
    mock_settings.openai_api_key = "sk-test-key"

    recipe = {"name": "Test", "ingredients": [], "time": 5, "steps": []}
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_mock_openai_response(recipe)
    )
    mock_openai_cls.return_value = mock_client

    file = ("file", ("img", BytesIO(b"\x00" * 64), content_type))
    response = client.post("/api/v1/upload-image/", files=[file])
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Billing
# ---------------------------------------------------------------------------

def test_mobile_payment_sheet_requires_auth():
    response = client.post("/api/v1/billing/mobile-payment-sheet", json={})
    assert response.status_code == 401


@patch("app.api.v1.endpoints.stripe.PaymentIntent.create")
@patch("app.api.v1.endpoints.stripe.EphemeralKey.create")
@patch("app.api.v1.endpoints.stripe.Customer.search")
@patch("app.api.v1.endpoints.settings")
def test_mobile_payment_sheet_success(
    mock_settings,
    mock_customer_search,
    mock_ephemeral_create,
    mock_intent_create,
):
    app.dependency_overrides[get_current_clerk_user] = lambda: {"user_id": "user_123", "claims": {}}
    mock_settings.stripe_secret_key = "sk_test"
    mock_settings.stripe_api_version = "2025-01-27.acacia"
    mock_settings.billing_default_amount_cents = 999
    mock_settings.billing_default_currency = "usd"
    mock_settings.billing_merchant_display_name = "STC Hackathon"
    mock_settings.billing_return_url = "stc://billing-return"

    mock_customer_search.return_value = {"data": [{"id": "cus_123"}]}
    mock_ephemeral_create.return_value = {"secret": "ephkey_secret"}
    mock_intent_create.return_value = {"client_secret": "pi_secret"}

    response = client.post(
        "/api/v1/billing/mobile-payment-sheet",
        json={"featureKey": "premium", "planKey": "pro", "source": "mobile"},
        headers={"Authorization": "Bearer fake-token"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["paymentIntentClientSecret"] == "pi_secret"
    assert payload["customerId"] == "cus_123"
    assert payload["customerEphemeralKeySecret"] == "ephkey_secret"
    assert payload["merchantDisplayName"] == "STC Hackathon"
    assert payload["returnUrl"] == "stc://billing-return"


@patch("app.api.v1.endpoints.stripe.billing_portal.Session.create")
@patch("app.api.v1.endpoints.stripe.Customer.search")
@patch("app.api.v1.endpoints.settings")
def test_customer_portal_success(mock_settings, mock_customer_search, mock_portal_create):
    app.dependency_overrides[get_current_clerk_user] = lambda: {"user_id": "user_123", "claims": {}}
    mock_settings.stripe_secret_key = "sk_test"
    mock_settings.stripe_api_version = "2025-01-27.acacia"
    mock_settings.billing_portal_return_url = "https://app.example.com/return"
    mock_settings.billing_return_url = ""

    mock_customer_search.return_value = {"data": [{"id": "cus_123"}]}
    mock_portal_create.return_value = {"url": "https://billing.example.com/session"}

    response = client.post(
        "/api/v1/billing/customer-portal",
        json={},
        headers={"Authorization": "Bearer fake-token"},
    )

    assert response.status_code == 200
    assert response.json() == {"url": "https://billing.example.com/session"}


@patch("app.api.v1.endpoints._update_clerk_public_metadata")
@patch("app.api.v1.endpoints._record_webhook_event")
@patch("app.api.v1.endpoints.stripe.Subscription.retrieve")
@patch("app.api.v1.endpoints.stripe.Webhook.construct_event")
@patch("app.api.v1.endpoints.settings")
def test_billing_webhook_checkout_completed(
    mock_settings,
    mock_construct_event,
    mock_subscription_retrieve,
    mock_record_event,
    mock_update_clerk_metadata,
):
    mock_settings.stripe_secret_key = "sk_test"
    mock_settings.stripe_api_version = "2025-01-27.acacia"
    mock_settings.stripe_webhook_secret = "whsec_test"

    mock_construct_event.return_value = {
        "id": "evt_123",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "metadata": {"clerk_user_id": "user_123"},
                "subscription": "sub_123",
            }
        },
    }
    mock_subscription_retrieve.return_value = {
        "status": "active",
        "current_period_end": 1735689600,
        "items": {"data": [{"price": {"nickname": "Meal Master Pro"}}]},
    }
    mock_record_event.return_value = True

    response = client.post(
        "/api/v1/billing/webhook",
        json={"any": "payload"},
        headers={"stripe-signature": "sig_test"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "processed", "eventId": "evt_123"}
    mock_update_clerk_metadata.assert_called_once()
    args = mock_update_clerk_metadata.call_args.args
    assert args[0] == "user_123"
    assert args[1]["subscriptionStatus"] == "active"
    assert args[1]["subscriptionPlan"] == "Meal Master Pro"
    assert args[1]["hasActiveSubscription"] is True


@patch("app.api.v1.endpoints._record_webhook_event")
@patch("app.api.v1.endpoints.stripe.Webhook.construct_event")
@patch("app.api.v1.endpoints.settings")
def test_billing_webhook_duplicate_event(mock_settings, mock_construct_event, mock_record_event):
    mock_settings.stripe_secret_key = "sk_test"
    mock_settings.stripe_api_version = "2025-01-27.acacia"
    mock_settings.stripe_webhook_secret = "whsec_test"

    mock_construct_event.return_value = {
        "id": "evt_dup",
        "type": "invoice.payment_failed",
        "data": {"object": {}},
    }
    mock_record_event.return_value = False

    response = client.post(
        "/api/v1/billing/webhook",
        json={"any": "payload"},
        headers={"stripe-signature": "sig_test"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "duplicate", "eventId": "evt_dup"}
