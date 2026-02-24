from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.v1.clerk_auth import ClerkAuthContext, get_current_clerk_user
from app.main import app
from app.services.billing_store import BillingStore

client = TestClient(app)


@pytest.fixture(autouse=True)
def _auth_override():
    app.dependency_overrides[get_current_clerk_user] = lambda: ClerkAuthContext(
        user_id="user_123", session_id="sess_123"
    )
    yield
    app.dependency_overrides.clear()


def test_mobile_payment_sheet_requires_auth_when_missing_bearer():
    app.dependency_overrides.clear()
    response = client.post("/api/v1/billing/mobile-payment-sheet", json={})
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "AUTH_INVALID_TOKEN"


@patch("app.api.v1.billing_endpoints.billing_service.create_mobile_payment_sheet")
def test_mobile_payment_sheet_success(mock_create):
    mock_create.return_value = {
        "paymentIntentClientSecret": "pi_secret_123",
        "customerId": "cus_123",
        "customerEphemeralKeySecret": "ephkey_123",
        "merchantDisplayName": "MealMaker",
        "returnUrl": "mealmaker://billing-return",
    }

    response = client.post(
        "/api/v1/billing/mobile-payment-sheet",
        json={"planKey": "meal-master-pro", "source": "mobile"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["paymentIntentClientSecret"] == "pi_secret_123"
    assert data["customerId"] == "cus_123"
    assert data["customerEphemeralKeySecret"] == "ephkey_123"


@patch("app.api.v1.billing_endpoints.billing_service.create_customer_portal")
def test_customer_portal_success(mock_portal):
    mock_portal.return_value = {"url": "https://billing.stripe.com/session/abc"}
    response = client.post("/api/v1/billing/customer-portal", json={"returnUrl": "app://settings"})
    assert response.status_code == 200
    assert response.json()["url"].startswith("https://billing.stripe.com/")


@patch("app.api.v1.billing_endpoints.billing_service.get_subscription_status")
def test_subscription_status_success(mock_status):
    mock_status.return_value = {
        "hasActiveSubscription": True,
        "status": "active",
        "planName": "Meal Master Pro",
        "currentPeriodEnd": "2026-12-01T00:00:00+00:00",
    }
    response = client.get("/api/v1/billing/subscription-status")
    assert response.status_code == 200
    assert response.json()["hasActiveSubscription"] is True
    assert response.json()["status"] == "active"


@patch("app.api.v1.billing_endpoints.billing_service.process_webhook_event")
@patch("app.api.v1.billing_endpoints.billing_service.construct_webhook_event")
def test_webhook_duplicate_event(mock_construct, mock_process):
    mock_construct.return_value = {"id": "evt_1", "type": "customer.subscription.updated", "data": {"object": {}}}
    mock_process.return_value = {"received": True, "idempotent": True}

    response = client.post(
        "/api/v1/billing/webhook",
        data=b"{}",
        headers={"Stripe-Signature": "t=1,v1=abc"},
    )
    assert response.status_code == 200
    assert response.json()["idempotent"] is True


@patch("app.api.v1.billing_endpoints.billing_service.construct_webhook_event")
def test_webhook_invalid_signature_returns_clear_error(mock_construct):
    mock_construct.side_effect = HTTPException(
        status_code=400,
        detail={
            "code": "BILLING_WEBHOOK_SIGNATURE_INVALID",
            "message": "Stripe webhook signature verification failed.",
        },
    )

    response = client.post(
        "/api/v1/billing/webhook",
        data=b"{}",
        headers={"Stripe-Signature": "bad-signature"},
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "BILLING_WEBHOOK_SIGNATURE_INVALID"


def test_billing_store_idempotency(tmp_path):
    store = BillingStore(str(tmp_path / "billing.sqlite3"))
    assert store.mark_event_started("evt_123") is True
    assert store.mark_event_started("evt_123") is False
    store.unmark_event("evt_123")
    assert store.mark_event_started("evt_123") is True
