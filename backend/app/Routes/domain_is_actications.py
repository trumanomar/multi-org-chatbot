from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.DB.db import get_db
from app.Models.tables import Domain

router = APIRouter(prefix="/admin/domain", tags=["domains"])

@router.patch("/{domains_id}/activate")
def activate_doc(domains_id: int, db: Session = Depends(get_db)):
    domain = db.query(Domain).filter(Domain.id == domains_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Document not found")
    domain.active = True
    db.commit()
    db.refresh(domain)
    return {"message": "Domian activated", "Domian": {"id": domain.id, "active": domain.active}}

@router.patch("/{domains_id}/deactivate")
def deactivate_doc(domains_id: int, db: Session = Depends(get_db)):
    domain = db.query(Domain).filter(Domain.id == domains_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Document not found")
    domain.active = False
    db.commit()
    db.refresh(domain)
    return {"message": "Domian deactivated", "Domian": {"id": domain.id, "active": domain.active}}
