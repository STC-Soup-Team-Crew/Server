from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.models import User  # Assuming you have a User model

def get_current_user(db: Session = Depends(get_db), user_id: int):
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# Add other dependency functions as needed