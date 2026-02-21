from pydantic import BaseModel
from typing import List, Optional

class ItemBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    tax: Optional[float] = None

class ItemCreate(ItemBase):
    pass

class Item(ItemBase):
    id: int

    class Config:
        orm_mode = True

class UserBase(BaseModel):
    username: str
    email: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int

    class Config:
        orm_mode = True

class Message(BaseModel):
    message: str


class ImageAnalysisResponse(BaseModel):
    """Generic wrapper for the external image-processing API response."""
    result: Optional[dict] = None
    error: Optional[str] = None