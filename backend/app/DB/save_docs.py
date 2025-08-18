# app/DB/save_docs.py
from sqlalchemy.orm import Session
from app.Models.tables import Docs

def save_document(db: Session, *, filename: str, user_id: int, domain_id: int) -> Docs:
    """
    Insert a single Docs row using the caller's DB session.
    Returns the persisted Docs object (with id populated).
    """
    doc = Docs(name=filename, user_id=user_id, domain_id=domain_id)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc
