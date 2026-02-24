import base64
import json
import logging
import re
from datetime import datetime, timezone

import httpx
import stripe
from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from openai import AsyncOpenAI

from typing import Any, List, Optional

from app.api.v1.deps import get_current_clerk_user
from app.core.config import settings
import app.db.session as supabase_db
import app.db.supabase_db as billing_db
from app.schemas.schemas import (
    ClaimRequest,
    CustomerPortalRequest,
    FavoriteRecipe,
    FridgeListingCreate,
    ItemBase,
    MobilePaymentSheetRequest,
)

router = APIRouter()
logger = logging.getLogger(__name__)

# Updated prompt to enforce the exact JSON schema and stringified arrays
PROMPT = (
    "Please break down the ingredients in this image (e.g. 3 tomatoes, 2 cucumbers, "
    "10 avocados, etc...) and generate a recipe that can be made with THESE ingredients. "
    "It doesn't need to use every ingredient, but it should not use additional ingredients. "
    "IMPORTANT: Each ingredient MUST include its amount (e.g., '2 cups Flour' instead of just 'Flour'). "
    "If the image is unclear or you cannot identify specific items, make your absolute best guess based on the context of the image. "
    "DO NOT apologize, DO NOT ask for clarification, and DO NOT output any conversational text. "
    "Please return ONLY the recipe as a JSON array containing a single object with the exact following schema: "
    '[{"Name": "string", "Steps": "stringified array of strings", "Time": integer, "Ingredients": "stringified array of strings"}]. '
    "Example exactly like this: "
    '[{"Name":"15-Minute Pancakes","Steps":"[\\"Whisk dry ingredients\\",\\"Add milk and eggs\\",\\"Cook on buttered skillet\\"]","Time":15,"Ingredients":"[\\"1 cup Flour\\",\\"2 Eggs\\",\\"0.5 cup Milk\\",\\"1 tbsp Butter\\"]"}]'
)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


# ---------- Billing helpers ----------

def _value(data: Any, key: str, default: Any = None) -> Any:
    if isinstance(data, dict):
        return data.get(key, default)
    if hasattr(data, "get"):
        try:
            return data.get(key, default)
        except TypeError:
            pass
    return getattr(data, key, default)


def _to_iso(timestamp: Any) -> str | None:
    if not timestamp:
        return None
    try:
        return datetime.fromtimestamp(int(timestamp), tz=timezone.utc).isoformat()
    except Exception:
        return None


def _configure_stripe() -> None:
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=500, detail="Stripe secret key is not configured.")
    stripe.api_key = settings.stripe_secret_key
    if settings.stripe_api_version:
        stripe.api_version = settings.stripe_api_version


def _get_or_create_stripe_customer(clerk_user: dict) -> Any:
    _configure_stripe()
    clerk_user_id = clerk_user["user_id"]
    claims = clerk_user.get("claims", {})

    try:
        query = f"metadata['clerk_user_id']:'{clerk_user_id}'"
        existing = stripe.Customer.search(query=query, limit=1)
        existing_data = _value(existing, "data", [])
        if existing_data:
            return existing_data[0]
    except Exception as exc:
        logger.warning("Stripe customer search failed for %s: %s", clerk_user_id, exc)

    customer_payload = {"metadata": {"clerk_user_id": clerk_user_id}}
    email = claims.get("email")
    if email:
        customer_payload["email"] = email
    return stripe.Customer.create(**customer_payload)


def _record_webhook_event(event_id: str, event_type: str) -> bool:
    conn = billing_db.get_connection()
    if conn is None:
        raise HTTPException(
            status_code=500,
            detail="Webhook idempotency storage is unavailable.",
        )

    cur = None
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS stripe_webhook_events (
                event_id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                processed_at TIMESTAMPTZ DEFAULT now()
            );
            """
        )
        cur.execute(
            """
            INSERT INTO stripe_webhook_events (event_id, event_type)
            VALUES (%s, %s)
            ON CONFLICT (event_id) DO NOTHING
            RETURNING event_id;
            """,
            (event_id, event_type),
        )
        inserted = cur.fetchone() is not None
        conn.commit()
        return inserted
    except Exception as exc:
        conn.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Webhook idempotency check failed: {exc}",
        )
    finally:
        if cur:
            cur.close()
        conn.close()


def _extract_plan_name(subscription: Any) -> str | None:
    items = _value(_value(subscription, "items", {}), "data", []) or []
    if not items:
        return None
    price = _value(items[0], "price", {}) or {}
    return _value(price, "nickname") or _value(price, "id")


def _build_subscription_metadata(subscription: Any, status_override: str | None = None) -> dict:
    status = status_override or _value(subscription, "status", "inactive")
    payload = {
        "subscriptionStatus": status,
        "hasActiveSubscription": status in {"active", "trialing"},
    }
    plan = _extract_plan_name(subscription)
    if plan:
        payload["subscriptionPlan"] = plan
    current_period_end = _to_iso(_value(subscription, "current_period_end"))
    if current_period_end:
        payload["currentPeriodEnd"] = current_period_end
    return payload


def _resolve_clerk_user_id_from_customer(customer_id: str | None) -> str | None:
    if not customer_id:
        return None
    customer = stripe.Customer.retrieve(customer_id)
    customer_metadata = _value(customer, "metadata", {}) or {}
    return customer_metadata.get("clerk_user_id")


def _extract_clerk_user_id(data_object: Any) -> str | None:
    metadata = _value(data_object, "metadata", {}) or {}
    return metadata.get("clerk_user_id") or _value(data_object, "client_reference_id")


def _update_clerk_public_metadata(clerk_user_id: str, metadata: dict) -> None:
    if not settings.clerk_secret_key:
        raise HTTPException(status_code=500, detail="Clerk secret key is not configured.")

    url = f"{settings.clerk_api_base_url.rstrip('/')}/users/{clerk_user_id}/metadata"
    headers = {
        "Authorization": f"Bearer {settings.clerk_secret_key}",
        "Content-Type": "application/json",
    }
    response = httpx.patch(url, headers=headers, json={"public_metadata": metadata}, timeout=15.0)
    if response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to update Clerk metadata: {response.text}",
        )


def _handle_billing_webhook_event(event_type: str, data_object: Any) -> None:
    if event_type == "checkout.session.completed":
        clerk_user_id = _extract_clerk_user_id(data_object)
        if not clerk_user_id:
            clerk_user_id = _resolve_clerk_user_id_from_customer(_value(data_object, "customer"))
        if not clerk_user_id:
            return
        subscription_id = _value(data_object, "subscription")
        metadata = {"subscriptionStatus": "active", "hasActiveSubscription": True}
        if subscription_id:
            subscription = stripe.Subscription.retrieve(subscription_id)
            metadata = _build_subscription_metadata(subscription)
        _update_clerk_public_metadata(clerk_user_id, metadata)
        return

    if event_type in {"customer.subscription.created", "customer.subscription.updated"}:
        clerk_user_id = _extract_clerk_user_id(data_object)
        if not clerk_user_id:
            clerk_user_id = _resolve_clerk_user_id_from_customer(_value(data_object, "customer"))
        if not clerk_user_id:
            return
        _update_clerk_public_metadata(clerk_user_id, _build_subscription_metadata(data_object))
        return

    if event_type == "customer.subscription.deleted":
        clerk_user_id = _extract_clerk_user_id(data_object)
        if not clerk_user_id:
            clerk_user_id = _resolve_clerk_user_id_from_customer(_value(data_object, "customer"))
        if not clerk_user_id:
            return
        deleted_metadata = _build_subscription_metadata(data_object, status_override="inactive")
        deleted_metadata["hasActiveSubscription"] = False
        _update_clerk_public_metadata(clerk_user_id, deleted_metadata)
        return

    if event_type == "invoice.payment_failed":
        clerk_user_id = _extract_clerk_user_id(data_object)
        if not clerk_user_id:
            clerk_user_id = _resolve_clerk_user_id_from_customer(_value(data_object, "customer"))
        if not clerk_user_id:
            return
        failed_metadata = {"subscriptionStatus": "past_due", "hasActiveSubscription": False}
        subscription_id = _value(data_object, "subscription")
        if subscription_id:
            subscription = stripe.Subscription.retrieve(subscription_id)
            failed_metadata = _build_subscription_metadata(subscription, status_override="past_due")
            failed_metadata["hasActiveSubscription"] = False
        _update_clerk_public_metadata(clerk_user_id, failed_metadata)


# ---------- Billing endpoints ----------

@router.post("/billing/mobile-payment-sheet")
async def create_mobile_payment_sheet(
    body: MobilePaymentSheetRequest,
    clerk_user: dict = Depends(get_current_clerk_user),
):
    try:
        customer = _get_or_create_stripe_customer(clerk_user)
        customer_id = _value(customer, "id")
        ephemeral_key = stripe.EphemeralKey.create(
            customer=customer_id,
            stripe_version=settings.stripe_api_version,
        )
        payment_intent = stripe.PaymentIntent.create(
            amount=settings.billing_default_amount_cents,
            currency=settings.billing_default_currency,
            customer=customer_id,
            automatic_payment_methods={"enabled": True},
            metadata={
                "clerk_user_id": clerk_user["user_id"],
                "featureKey": body.featureKey or "",
                "planKey": body.planKey or "",
                "source": body.source or "",
            },
        )
        response = {
            "paymentIntentClientSecret": _value(payment_intent, "client_secret"),
            "customerId": customer_id,
            "customerEphemeralKeySecret": _value(ephemeral_key, "secret"),
        }
        if settings.billing_merchant_display_name:
            response["merchantDisplayName"] = settings.billing_merchant_display_name
        if settings.billing_return_url:
            response["returnUrl"] = settings.billing_return_url
        return response
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed creating mobile payment sheet for user %s", clerk_user["user_id"])
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create mobile payment sheet: {exc}",
        )


@router.post("/billing/customer-portal")
async def create_customer_portal(
    body: CustomerPortalRequest,
    clerk_user: dict = Depends(get_current_clerk_user),
):
    try:
        customer = _get_or_create_stripe_customer(clerk_user)
        customer_id = _value(customer, "id")
        return_url = body.returnUrl or settings.billing_portal_return_url or settings.billing_return_url
        if not return_url:
            raise HTTPException(
                status_code=500,
                detail="Billing portal return URL is not configured.",
            )
        portal_session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )
        return {"url": _value(portal_session, "url")}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed creating customer portal for user %s", clerk_user["user_id"])
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create customer portal session: {exc}",
        )


@router.post("/billing/webhook")
async def billing_webhook(request: Request):
    _configure_stripe()
    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=500, detail="Stripe webhook secret is not configured.")

    payload = await request.body()
    signature = request.headers.get("stripe-signature")
    if not signature:
        raise HTTPException(status_code=400, detail="Missing stripe-signature header.")

    try:
        event = stripe.Webhook.construct_event(payload, signature, settings.stripe_webhook_secret)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid webhook payload: {exc}")
    except stripe.error.SignatureVerificationError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid webhook signature: {exc}")

    event_id = _value(event, "id")
    event_type = _value(event, "type", "")
    if not event_id:
        raise HTTPException(status_code=400, detail="Webhook event id is missing.")

    if not _record_webhook_event(event_id, event_type):
        return {"status": "duplicate", "eventId": event_id}

    try:
        data_object = _value(_value(event, "data", {}), "object", {})
        _handle_billing_webhook_event(event_type, data_object)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed processing Stripe webhook event %s", event_id)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process webhook event: {exc}",
        )

    return {"status": "processed", "eventId": event_id}


# ---------- Existing item endpoints ----------

@router.get("/items/")
async def read_items():
    return [{"item_id": 1, "name": "Item 1"}, {"item_id": 2, "name": "Item 2"}]


@router.post("/items/")
async def create_item(item: dict):
    return {"item_id": 3, "name": item["name"]}


@router.post("/recipes/save")
async def save_recipe(recipe: ItemBase):
    supabase_db.save_item_to_db(recipe)


@router.post("/recipes/favorite")
async def favorite_recipe(favorite: FavoriteRecipe):
    return supabase_db.save_favorite_to_db(favorite)

@router.get("/recipes/favorite")
async def get_favorites(user_id: str):
    return supabase_db.get_favorites_from_db(user_id)


@router.get("/recipes/search")
async def search_recipes(ingredients: str):
    """Search recipes by ingredients. Pass a comma-separated list, e.g. ?ingredients=tomato,cheese"""
    ingredient_list = [i.strip() for i in ingredients.split(",") if i.strip()]
    return supabase_db.search_recipes_by_ingredients(ingredient_list)

# ---------- Fridge Share (leftover sharing) ----------

@router.post("/fridge-listings")
async def create_fridge_listing(listing: FridgeListingCreate):
    """Post a new leftover-item listing to the community feed."""
    try:
        created = supabase_db.create_fridge_listing(listing)
        return created
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to create listing: {exc}")


@router.get("/fridge-listings")
async def get_fridge_listings(status: Optional[str] = Query("available")):
    """Get all fridge listings, optionally filtered by status (default: available)."""
    return supabase_db.get_fridge_listings(status)


@router.get("/fridge-listings/mine")
async def get_my_listings(user_id: str = Query(...)):
    """Get all listings posted by the authenticated user."""
    return supabase_db.get_user_fridge_listings(user_id)


@router.get("/fridge-listings/{listing_id}")
async def get_fridge_listing(listing_id: str):
    """Get a single listing by ID."""
    listing = supabase_db.get_fridge_listing_by_id(listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing


@router.patch("/fridge-listings/{listing_id}/claim")
async def claim_fridge_listing(listing_id: str, body: ClaimRequest):
    """Claim an available listing. Fails if already claimed."""
    try:
        result = supabase_db.claim_fridge_listing(listing_id, body.claimed_by, body.claimed_by_name)
        if not result:
            raise HTTPException(status_code=409, detail="Listing is no longer available")
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to claim listing: {exc}")


@router.delete("/fridge-listings/{listing_id}")
async def delete_fridge_listing(listing_id: str, user_id: str = Query(...)):
    """Soft-delete a listing (owner only)."""
    try:
        deleted = supabase_db.delete_fridge_listing(listing_id, user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Listing not found or not owned by you")
        return {"detail": "Listing deleted"}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to delete listing: {exc}")

# ---------- Image upload → ChatGPT vision ----------

@router.post("/upload-image/")
async def upload_image(file: UploadFile = File(...)):
    """
    Receive an image from the frontend, send it to ChatGPT with a recipe prompt,
    and return the parsed JSON recipe.
    """
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. "
                   f"Allowed: {', '.join(ALLOWED_CONTENT_TYPES)}",
        )

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({len(contents)} bytes). Max is {MAX_FILE_SIZE} bytes.",
        )

    if not settings.openai_api_key and settings.model_url == "https://api.openai.com/v1":
        raise HTTPException(
            status_code=500,
            detail="OpenAI API key is not configured. Set OPENAI_API_KEY in .env",
        )

    image_b64 = base64.b64encode(contents).decode("utf-8")
    data_url = f"data:{file.content_type};base64,{image_b64}"

    client = AsyncOpenAI(
        api_key=settings.openai_api_key or "sk-dummy",
        base_url=settings.model_url,
    )

    try:
        completion = await client.chat.completions.create(
            model=settings.model_name,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": PROMPT},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
            response_format={"type": "text"},
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"OpenAI API error: {exc}")

    if not completion.choices:
        raise HTTPException(status_code=502, detail="ChatGPT returned an empty response (no choices).")

    raw = completion.choices[0].message.content
    if not raw:
        raise HTTPException(status_code=502, detail="ChatGPT returned an empty message content.")

    # Robust JSON extraction
    content = raw.strip()

    # Try to find JSON block in markdown
    if "```" in content:
        # Extract the content between the first and last triple backticks
        match = re.search(r"```(?:json)?\n?(.*?)\n?```", content, re.DOTALL)
        if match:
            content = match.group(1).strip()

    # Try parsing directly
    try:
        recipe_data = json.loads(content)
        return recipe_data
    except json.JSONDecodeError:
        pass  # Continue to fallback

    # Fallback: Try to find the first '[' or '{' and the last ']' or '}' 
    # and parse the content between them.
    for start_char, end_char in [("[", "]"), ("{", "}")]:
        start_idx = content.find(start_char)
        end_idx = content.rfind(end_char)

        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            try:
                recipe_data = json.loads(content[start_idx : end_idx + 1])
                return recipe_data
            except json.JSONDecodeError:
                continue

    raise HTTPException(status_code=502, detail=f"ChatGPT returned invalid JSON: {raw}")
