# app/DB/save_chunks.py - Enhanced version with debugging
from __future__ import annotations
from typing import List, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
from app.Models.tables import Chunk
import json

def save_chunks(
    db: Session,
    *,
    chunks_list: List[Any],
    doc_id: int,
    user_id: int,
    domain_id: int,
    batch_size: int = 500,
) -> List[Chunk]:
    """
    Persist chunk rows for a single document using the caller's DB session.
    Enhanced with debugging to track what's actually happening.
    """
    print(f"[save_chunks] Starting with {len(chunks_list)} chunks")
    print(f"[save_chunks] doc_id={doc_id}, user_id={user_id}, domain_id={domain_id}")
    
    # 1. Verify chunks table exists
    try:
        result = db.execute(text("SHOW TABLES LIKE 'chunk%'"))
        tables = result.fetchall()
        print(f"[save_chunks] Tables matching 'chunk%': {[t[0] for t in tables]}")
        
        # Check chunks table structure
        result = db.execute(text("DESCRIBE chunks"))
        columns = result.fetchall()
        print(f"[save_chunks] Chunks table columns: {[col[0] for col in columns]}")
        
        # Check current chunk count
        result = db.execute(text("SELECT COUNT(*) FROM chunks"))
        current_count = result.fetchone()[0]
        print(f"[save_chunks] Current chunks in database: {current_count}")
        
    except Exception as e:
        print(f"[save_chunks] ERROR checking table: {e}")
        raise
    
    created: List[Chunk] = []
    batch: List[Chunk] = []

    def _flush_batch():
        if not batch:
            return
        
        print(f"[save_chunks] Flushing batch of {len(batch)} chunks")
        try:
            # Add to session
            db.add_all(batch)
            print(f"[save_chunks] Added {len(batch)} chunks to session")
            
            # Commit
            db.commit()
            print(f"[save_chunks] Committed batch successfully")
            
            # Refresh to get IDs
            for row in batch:
                db.refresh(row)
                created.append(row)
                print(f"[save_chunks] Refreshed chunk with ID: {row.id}")
            
            # Verify they're actually in the database
            try:
                result = db.execute(text("SELECT COUNT(*) FROM chunks WHERE doc_id = :doc_id"), {"doc_id": doc_id})
                count_in_db = result.fetchone()[0]
                print(f"[save_chunks] Chunks for doc_id {doc_id} now in DB: {count_in_db}")
            except Exception as verify_error:
                print(f"[save_chunks] ERROR verifying chunks in DB: {verify_error}")
            
            batch.clear()
            
        except SQLAlchemyError as e:
            print(f"[save_chunks] SQLAlchemy ERROR in flush_batch: {e}")
            db.rollback()
            raise
        except Exception as e:
            print(f"[save_chunks] GENERAL ERROR in flush_batch: {e}")
            db.rollback()
            raise

    # Process each chunk
    for i, d in enumerate(chunks_list or []):
        if isinstance(d, dict):  # لو dict
            content = d.get("content", "")
            metadata = d.get("metadata", {}) or {}
        else:  # غالبًا Document
            content = getattr(d, "page_content", "") or getattr(d, "content", "") or ""
            metadata = getattr(d, "metadata", {}) or {}

        print(f"[save_chunks] Processing chunk {i+1}: content_length={len(content)}")
        print(f"[save_chunks] Chunk {i+1} preview: {content[:100]}...")
        print(f"[save_chunks] Metadata keys: {list(metadata.keys())}")

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

    # Flush remaining
    _flush_batch()
    
    print(f"[save_chunks] Final result: created {len(created)} chunks")
    
    # Final verification
    try:
        result = db.execute(text("SELECT COUNT(*) FROM chunks WHERE doc_id = :doc_id"), {"doc_id": doc_id})
        final_count = result.fetchone()[0]
        print(f"[save_chunks] FINAL VERIFICATION: {final_count} chunks for doc_id {doc_id}")
        
        # Show a sample of what was saved
        result = db.execute(text("""
            SELECT id, LEFT(content, 50) as content_preview, LEFT(meta_data, 100) as metadata_preview 
            FROM chunks 
            WHERE doc_id = :doc_id 
            LIMIT 3
        """), {"doc_id": doc_id})
        sample_chunks = result.fetchall()
        print(f"[save_chunks] Sample saved chunks:")
        for chunk in sample_chunks:
            print(f"  ID: {chunk[0]}, Content: {chunk[1]}..., Metadata: {chunk[2]}...")
            
    except Exception as verify_error:
        print(f"[save_chunks] ERROR in final verification: {verify_error}")
    
    return created