from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.DB.db import get_db
from app.Models.tables import Feedback, User
from app.auth.schemas import FeedbackResponse
from app.auth.dependencies import get_current_user_db, require_user

app = APIRouter(
    prefix="/feedback",
    tags=["feedback"]
)


# get feedback for the current user
@app.get("/get", response_model=List[FeedbackResponse], dependencies=[Depends(require_user)])

async def get_feedback(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_db)
):
    feedbacks = db.query(Feedback).filter(Feedback.user_id == current_user.id).all()
    return feedbacks
