from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.models import YourModel  # Replace with your actual model
from app.schemas.schemas import YourModelCreate, YourModelUpdate  # Replace with your actual schemas

def create_item(db: Session, item: YourModelCreate) -> YourModel:
    db_item = YourModel(**item.dict())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

def get_item(db: Session, item_id: int) -> Optional[YourModel]:
    return db.query(YourModel).filter(YourModel.id == item_id).first()

def get_items(db: Session, skip: int = 0, limit: int = 10) -> List[YourModel]:
    return db.query(YourModel).offset(skip).limit(limit).all()

def update_item(db: Session, item_id: int, item: YourModelUpdate) -> Optional[YourModel]:
    db_item = db.query(YourModel).filter(YourModel.id == item_id).first()
    if db_item:
        for key, value in item.dict(exclude_unset=True).items():
            setattr(db_item, key, value)
        db.commit()
        db.refresh(db_item)
    return db_item

def delete_item(db: Session, item_id: int) -> Optional[YourModel]:
    db_item = db.query(YourModel).filter(YourModel.id == item_id).first()
    if db_item:
        db.delete(db_item)
        db.commit()
    return db_item