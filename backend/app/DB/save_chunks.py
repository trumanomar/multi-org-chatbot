# app/DB/save_chunks.py
from __future__ import annotations
from typing import List, Any
from sqlalchemy.orm import Session
from app.Models.tables import Chunk
import json

def save_chunks(
    db: Session,
    *,
    chunks_list: List[Any],   # usually List[langchain.docstore.document.Document]
    doc_id: int,
    user_id: int,
    domain_id: int,
    batch_size: int = 500,
) -> List[Chunk]:
    """
    Persist chunk rows for a single document using the caller's DB session.
    `meta_data` is stored as JSON text.

    Returns the list of created Chunk rows (ids populated).
    """
    created: List[Chunk] = []
    batch: List[Chunk] = []

    def _flush_batch():
        if not batch:
            return
        db.add_all(batch)
        db.commit()
        for row in batch:
            db.refresh(row)
            created.append(row)
        batch.clear()

    for d in (chunks_list or []):
        content = getattr(d, "page_content", "") or ""
        metadata = getattr(d, "metadata", None) or {}
        row = Chunk(
            content=content,
            meta_data=json.dumps(metadata, ensure_ascii=False),
            user_id=user_id,
            domain_id=domain_id,
            doc_id=doc_id,
        )
        batch.append(row)
        if len(batch) >= batch_size:
            _flush_batch()

    _flush_batch()
    return created
