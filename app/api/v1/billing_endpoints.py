import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.v1.clerk_auth import ClerkAuthContext, get_current_clerk_user
from app.schemas.billing_schemas import (
    CustomerPortalRequest,
    CustomerPortalResponse,
    MobilePaymentSheetRequest,
    MobilePaymentSheetResponse,
)
from app.services import billing_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/billing", tags=["Billing"])


@router.post("/mobile-payment-sheet", response_model=MobilePaymentSheetResponse)
async def create_mobile_payment_sheet(
    body: MobilePaymentSheetRequest,
    auth: ClerkAuthContext = Depends(get_current_clerk_user),
):
    try:
        return billing_service.create_mobile_payment_sheet(auth.user_id, body.model_dump())
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to create mobile payment sheet", extra={"user_id": auth.user_id})
        raise HTTPException(
            status_code=500,
            detail={"code": "BILLING_PAYMENT_SHEET_FAILED", "message": f"Failed to create payment sheet: {exc}"},
        ) from exc


@router.post("/customer-portal", response_model=CustomerPortalResponse)
async def create_customer_portal(
    body: CustomerPortalRequest,
    auth: ClerkAuthContext = Depends(get_current_clerk_user),
):
    try:
        return billing_service.create_customer_portal(auth.user_id, body.returnUrl)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to create customer portal", extra={"user_id": auth.user_id})
        raise HTTPException(
            status_code=500,
            detail={"code": "BILLING_PORTAL_FAILED", "message": f"Failed to create customer portal: {exc}"},
        ) from exc


@router.post("/webhook")
async def handle_billing_webhook(request: Request):
    payload = await request.body()
    stripe_signature = request.headers.get("Stripe-Signature")
    try:
        event = billing_service.construct_webhook_event(payload, stripe_signature)
        return billing_service.process_webhook_event(event)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to handle billing webhook")
        raise HTTPException(
            status_code=500,
            detail={"code": "BILLING_WEBHOOK_FAILED", "message": f"Unexpected webhook error: {exc}"},
        ) from exc
