import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

import requests
from fastapi import HTTPException

from app.core.config import settings
from app.services.billing_store import BillingStore

try:
    import stripe
except ImportError:  # pragma: no cover - handled at runtime
    stripe = None

logger = logging.getLogger(__name__)
store = BillingStore(settings.billing_sqlite_path)


def _obj_get(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    try:
        return obj.get(key, default)
    except Exception:
        return getattr(obj, key, default)


def _error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})


def _require_stripe() -> None:
    if stripe is None:
        raise _error(500, "BILLING_STRIPE_MISSING", "Stripe SDK is not installed on the server.")
    if not settings.stripe_secret_key:
        raise _error(500, "BILLING_STRIPE_NOT_CONFIGURED", "Stripe secret key is not configured.")
    stripe.api_key = settings.stripe_secret_key
    stripe.api_version = settings.stripe_api_version


def _to_iso_utc(timestamp: Optional[int]) -> Optional[str]:
    if not timestamp:
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


def _extract_plan_name(subscription_obj: Any) -> Optional[str]:
    items = _obj_get(_obj_get(subscription_obj, "items", {}), "data", []) or []
    if not items:
        return None
    price = _obj_get(items[0], "price", {})
    nickname = _obj_get(price, "nickname")
    if nickname:
        return nickname
    product = _obj_get(price, "product")
    if isinstance(product, dict):
        return product.get("name") or product.get("id")
    return _obj_get(price, "id")


def _clerk_user_from_customer(customer_id: Optional[str]) -> Optional[str]:
    if not customer_id:
        return None
    customer = stripe.Customer.retrieve(customer_id)
    metadata = _obj_get(customer, "metadata", {}) or {}
    return metadata.get("clerk_user_id")


def _resolve_clerk_user_id(payload_object: Any) -> Optional[str]:
    metadata = _obj_get(payload_object, "metadata", {}) or {}
    clerk_user_id = metadata.get("clerk_user_id")
    if clerk_user_id:
        return clerk_user_id

    customer_obj = _obj_get(payload_object, "customer")
    if isinstance(customer_obj, dict):
        customer_metadata = customer_obj.get("metadata", {}) or {}
        if customer_metadata.get("clerk_user_id"):
            return customer_metadata["clerk_user_id"]
        customer_id = customer_obj.get("id")
    else:
        customer_id = customer_obj

    return _clerk_user_from_customer(customer_id)


def _upsert_clerk_public_metadata(clerk_user_id: str, metadata: Dict[str, Any]) -> None:
    if not settings.clerk_secret_key:
        raise _error(500, "BILLING_CLERK_NOT_CONFIGURED", "Clerk secret key is not configured.")
    url = f"{settings.clerk_api_url.rstrip('/')}/users/{clerk_user_id}/metadata"
    headers = {
        "Authorization": f"Bearer {settings.clerk_secret_key}",
        "Content-Type": "application/json",
    }
    response = requests.patch(url, headers=headers, json={"public_metadata": metadata}, timeout=15)
    if response.status_code >= 400:
        raise _error(
            502,
            "BILLING_CLERK_UPDATE_FAILED",
            f"Clerk metadata update failed ({response.status_code}): {response.text}",
        )


def _build_subscription_metadata(subscription_obj: Any) -> Dict[str, Any]:
    status = _obj_get(subscription_obj, "status", "inactive")
    metadata: Dict[str, Any] = {
        "subscriptionStatus": status,
        "subscriptionPlan": _extract_plan_name(subscription_obj) or "Unknown",
        "hasActiveSubscription": status in {"active", "trialing"},
    }
    current_period_end = _to_iso_utc(_obj_get(subscription_obj, "current_period_end"))
    if current_period_end:
        metadata["currentPeriodEnd"] = current_period_end
    return metadata


def _build_event_update(event_type: str, payload_object: Any) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    if event_type in {"customer.subscription.created", "customer.subscription.updated"}:
        return _resolve_clerk_user_id(payload_object), _build_subscription_metadata(payload_object)

    if event_type == "customer.subscription.deleted":
        metadata: Dict[str, Any] = {
            "subscriptionStatus": "inactive",
            "hasActiveSubscription": False,
        }
        return _resolve_clerk_user_id(payload_object), metadata

    if event_type == "invoice.payment_failed":
        invoice_plan = None
        lines = _obj_get(_obj_get(payload_object, "lines", {}), "data", []) or []
        if lines:
            price = _obj_get(lines[0], "price", {}) or {}
            invoice_plan = _obj_get(price, "nickname") or _obj_get(price, "id")
        metadata = {
            "subscriptionStatus": "past_due",
            "subscriptionPlan": invoice_plan or "Unknown",
            "hasActiveSubscription": False,
        }
        return _resolve_clerk_user_id(payload_object), metadata

    if event_type == "checkout.session.completed":
        subscription_id = _obj_get(payload_object, "subscription")
        if subscription_id:
            subscription = stripe.Subscription.retrieve(subscription_id, expand=["items.data.price.product"])
            return _resolve_clerk_user_id(subscription), _build_subscription_metadata(subscription)
        payment_status = _obj_get(payload_object, "payment_status")
        status = "active" if payment_status == "paid" else "inactive"
        session_metadata = _obj_get(payload_object, "metadata", {}) or {}
        metadata = {
            "subscriptionStatus": status,
            "subscriptionPlan": session_metadata.get("planKey") or session_metadata.get("plan_key") or "Unknown",
            "hasActiveSubscription": status in {"active", "trialing"},
        }
        return _resolve_clerk_user_id(payload_object), metadata

    return None, None


def get_or_create_customer(clerk_user_id: str) -> str:
    _require_stripe()
    existing_customer_id = store.get_customer_id(clerk_user_id)
    if existing_customer_id:
        try:
            customer = stripe.Customer.retrieve(existing_customer_id)
            if not _obj_get(customer, "deleted", False):
                return existing_customer_id
        except Exception:
            logger.warning("Existing Stripe customer lookup failed, creating a new customer.", exc_info=True)

    customer = stripe.Customer.create(metadata={"clerk_user_id": clerk_user_id})
    customer_id = _obj_get(customer, "id")
    if not customer_id:
        raise _error(502, "BILLING_CUSTOMER_CREATE_FAILED", "Stripe customer creation returned no id.")
    store.set_customer_id(clerk_user_id, customer_id)
    return customer_id


def create_mobile_payment_sheet(clerk_user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    _require_stripe()
    customer_id = get_or_create_customer(clerk_user_id)
    metadata = {"clerk_user_id": clerk_user_id}
    for key in ("featureKey", "planKey", "source"):
        value = payload.get(key)
        if value:
            metadata[key] = value

    ephemeral_key = stripe.EphemeralKey.create(
        customer=customer_id,
        stripe_version=settings.stripe_api_version,
    )
    payment_intent = stripe.PaymentIntent.create(
        amount=settings.billing_default_amount_cents,
        currency=settings.billing_default_currency,
        customer=customer_id,
        automatic_payment_methods={"enabled": True},
        setup_future_usage="off_session",
        metadata=metadata,
    )
    response: Dict[str, Any] = {
        "paymentIntentClientSecret": _obj_get(payment_intent, "client_secret"),
        "customerId": customer_id,
        "customerEphemeralKeySecret": _obj_get(ephemeral_key, "secret"),
    }
    if settings.billing_merchant_display_name:
        response["merchantDisplayName"] = settings.billing_merchant_display_name
    if settings.billing_return_url:
        response["returnUrl"] = settings.billing_return_url
    return response


def create_customer_portal(clerk_user_id: str, return_url: Optional[str]) -> Dict[str, str]:
    _require_stripe()
    customer_id = get_or_create_customer(clerk_user_id)
    resolved_return_url = return_url or settings.billing_return_url
    if not resolved_return_url:
        raise _error(
            400,
            "BILLING_RETURN_URL_REQUIRED",
            "A returnUrl is required when billing default return URL is not configured.",
        )
    portal_session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=resolved_return_url,
    )
    return {"url": _obj_get(portal_session, "url")}


def construct_webhook_event(payload: bytes, stripe_signature: Optional[str]) -> Any:
    _require_stripe()
    if not settings.stripe_webhook_secret:
        raise _error(500, "BILLING_WEBHOOK_NOT_CONFIGURED", "Stripe webhook secret is not configured.")
    if not stripe_signature:
        raise _error(400, "BILLING_WEBHOOK_SIGNATURE_MISSING", "Stripe-Signature header is required.")
    try:
        return stripe.Webhook.construct_event(payload, stripe_signature, settings.stripe_webhook_secret)
    except ValueError as exc:
        raise _error(400, "BILLING_WEBHOOK_PAYLOAD_INVALID", f"Invalid Stripe webhook payload: {exc}") from exc
    except Exception as exc:
        if exc.__class__.__name__ == "SignatureVerificationError":
            raise _error(
                400,
                "BILLING_WEBHOOK_SIGNATURE_INVALID",
                "Stripe webhook signature verification failed.",
            ) from exc
        raise


def process_webhook_event(event: Any) -> Dict[str, Any]:
    event_id = _obj_get(event, "id")
    event_type = _obj_get(event, "type")
    payload_object = _obj_get(_obj_get(event, "data", {}), "object", {})
    if not event_id:
        raise _error(400, "BILLING_WEBHOOK_EVENT_INVALID", "Webhook event does not include an id.")

    if not store.mark_event_started(event_id):
        return {"received": True, "idempotent": True}

    try:
        clerk_user_id, metadata_update = _build_event_update(event_type, payload_object)
        if clerk_user_id and metadata_update:
            _upsert_clerk_public_metadata(clerk_user_id, metadata_update)
        return {"received": True, "idempotent": False}
    except HTTPException:
        store.unmark_event(event_id)
        raise
    except Exception as exc:
        store.unmark_event(event_id)
        logger.exception("Unhandled webhook processing error", extra={"event_type": event_type, "event_id": event_id})
        raise _error(500, "BILLING_WEBHOOK_PROCESSING_FAILED", f"Failed to process webhook: {exc}") from exc
