from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.DB.db import get_db
from app.Models.tables import Docs

router = APIRouter(prefix="/admin/docs", tags=["docs"])

@router.patch("/{doc_id}/activate")
def activate_doc(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(Docs).filter(Docs.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    doc.active = True
    db.commit()
    db.refresh(doc)
    return {"message": "Document activated", "doc": {"id": doc.id, "active": doc.active}}

@router.patch("/{doc_id}/deactivate")
def deactivate_doc(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(Docs).filter(Docs.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    doc.active = False
    db.commit()
    db.refresh(doc)
    return {"message": "Document deactivated", "doc": {"id": doc.id, "active": doc.active}}
