from pydantic import BaseModel
from typing import List, Optional


class ItemBase(BaseModel):
    Name: str
    Steps: List[str]
    Ingredients: List[str]
    Time: int
    created_at: Optional[str] = None
