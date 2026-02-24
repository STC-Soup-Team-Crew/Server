from typing import Optional

from pydantic import BaseModel


class MobilePaymentSheetRequest(BaseModel):
    featureKey: Optional[str] = None
    planKey: Optional[str] = None
    source: Optional[str] = None


class MobilePaymentSheetResponse(BaseModel):
    paymentIntentClientSecret: str
    customerId: str
    customerEphemeralKeySecret: str
    merchantDisplayName: Optional[str] = None
    returnUrl: Optional[str] = None


class CustomerPortalRequest(BaseModel):
    returnUrl: Optional[str] = None


class CustomerPortalResponse(BaseModel):
    url: str
