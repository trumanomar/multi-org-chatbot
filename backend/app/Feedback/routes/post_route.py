from fastapi import APIRouter,  Depends
from sqlalchemy.orm import Session
from app.DB.db import get_db
from app.Models.tables import Feedback,User
from app.auth.dependencies import require_user
from app.auth.schemas import FeedbackCreate
from app.auth.dependencies import require_admin, get_current_user_db, Principal

app=APIRouter(prefix="/feedback",tags=["feedback"])
@app.post("/post",dependencies=[Depends(require_user)])
async def create_feedback(feedback: FeedbackCreate, db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user_db),   
):
    new_feedback = Feedback(
        user_id=current_user.id , # from JWT
        domain_id=current_user.domain_id, 
        content=feedback.content,
        rating=feedback.rating,
        question=feedback.question
    )
    db.add(new_feedback)
    db.commit()
    db.refresh(new_feedback)
    return new_feedback  
     
    
    
