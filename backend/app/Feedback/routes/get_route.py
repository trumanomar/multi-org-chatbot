from fastapi import APIRouter, Depends,HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.DB.db import get_db
from app.Models.tables import Feedback, User
from app.auth.schemas import FeedbackResponse
from app.auth.dependencies import get_current_user_db, require_admin,Principal

app = APIRouter(
    prefix="/feedback",
    tags=["feedback"],
)

# Admin get all feedback

@app.get("/get")
def get_feedback_for_admin(
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin),
):
    # admin domain id from token
    domain_id = principal.domain_id  

    # Fetch all feedback for the admin's domain
    feedbacks = (
        db.query(Feedback)
        .join(User, Feedback.user_id == User.id)
        .filter(User.domain_id == domain_id)
        .all()
    )

    if not feedbacks:
        raise HTTPException(status_code=404, detail="No feedback found for this domain")

    return feedbacks