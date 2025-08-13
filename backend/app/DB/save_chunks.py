from app.Models.tables import Chunk
from app.DB.db import SessionLocal
import json
def save_chunks(chunks_list, doc_id: int, user_id: int, domain_id: int):
    """
    chunks_list: list of LangChain Document objects
    """
    db = SessionLocal()
    try:
        for d in chunks_list:
            chunk = Chunk(
                content=d.page_content,
                meta_data=json.dumps(d.metadata),
                user_id=user_id,
                domain_id=domain_id,
                doc_id=doc_id
            )
            db.add(chunk)
        db.commit()
        return len(chunks_list)
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()
