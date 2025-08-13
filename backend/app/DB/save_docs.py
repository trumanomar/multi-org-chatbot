from app.Models.tables import Docs
from app.DB.db import SessionLocal

def save_document(filename: str, user_id: int, domain_id: int,  dict = None):
    db = SessionLocal()
    try:
        doc = Docs(
            name=filename,
            user_id=user_id,
            domain_id=domain_id,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        return doc
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()
