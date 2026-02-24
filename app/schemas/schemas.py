from pydantic import BaseModel
from typing import List, Optional


class ItemBase(BaseModel):
    Name: str
    Steps: List[str]
    Ingredients: List[str]
    Time: int
    created_at: Optional[str] = None

class FavoriteRecipe(ItemBase):
    user_id: str


# ---------- Fridge Share (leftover sharing) ----------

class FridgeListingCreate(BaseModel):
    """Payload for creating a new fridge listing."""
    user_id: str
    user_display_name: str
    title: str
    description: Optional[str] = None
    items: List[str]                   # e.g. ["3 tomatoes", "1 carton milk"]
    quantity: Optional[str] = None     # e.g. "enough for 2 meals"
    expiry_hint: Optional[str] = None  # e.g. "use within 2 days"
    pickup_instructions: Optional[str] = None  # e.g. "Meet at lobby"
    image_url: Optional[str] = None


class FridgeListingUpdate(BaseModel):
    """Payload for partially updating a listing (owner only)."""
    title: Optional[str] = None
    description: Optional[str] = None
    items: Optional[List[str]] = None
    quantity: Optional[str] = None
    expiry_hint: Optional[str] = None
    pickup_instructions: Optional[str] = None
    image_url: Optional[str] = None


class ClaimRequest(BaseModel):
    """Payload for claiming a fridge listing."""
    claimed_by: str              # user_id of claimer
    claimed_by_name: str         # display name of claimer


# ---------- Billing ----------

class MobilePaymentSheetRequest(BaseModel):
    featureKey: Optional[str] = None
    planKey: Optional[str] = None
    source: Optional[str] = None


class CustomerPortalRequest(BaseModel):
    returnUrl: Optional[str] = None
