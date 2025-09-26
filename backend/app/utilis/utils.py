import os
import json
import pandas as pd
from typing import List, Dict, Any
from langchain.docstore.document import Document
from docling.document_converter import DocumentConverter
from fastmcp import FastMCP

# Configuration
MAX_FILE_SIZE_MB = 100
CSV_ROWS_PER_DOC = 100  # Batch CSV rows to avoid memory issues


# --- Simple Chunker ---
def simple_chunk_text(text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> List[str]:
    """
    Chunk text into overlapping segments.
    
    Args:
        text: Input text to chunk
        chunk_size: Maximum size of each chunk
        chunk_overlap: Number of characters to overlap between chunks
        
    Returns:
        List of text chunks
        
    Raises:
        ValueError: If parameters are invalid
    """
    # Validate parameters
    if chunk_size <= 0:
        raise ValueError(f"chunk_size must be positive, got {chunk_size}")
    if chunk_overlap < 0:
        raise ValueError(f"chunk_overlap cannot be negative, got {chunk_overlap}")
    if chunk_overlap >= chunk_size:
        raise ValueError(
            f"chunk_overlap ({chunk_overlap}) must be less than chunk_size ({chunk_size})"
        )
    
    print(f"[utils] simple_chunk_text called with text length: {len(text)}")
    print(f"[utils] chunk_size: {chunk_size}, chunk_overlap: {chunk_overlap}")
    
    if not text or not text.strip():
        print(f"[utils] WARNING: Empty or whitespace-only text provided")
        return []
    
    chunks = []
    start = 0
    text_len = len(text)
    step = chunk_size - chunk_overlap
    
    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunk = text[start:end]
        stripped_chunk = chunk.strip()
        
        if stripped_chunk:
            chunks.append(stripped_chunk)
            print(f"[utils] Created chunk {len(chunks)}: length={len(stripped_chunk)}")
        
        start += step
    
    print(f"[utils] simple_chunk_text returning {len(chunks)} chunks")
    return chunks


# --- Docling Loader ---
def docling_to_docs(file_path: str) -> List[Document]:
    """
    Convert document to Document objects using Docling.
    
    Args:
        file_path: Path to document file
        
    Returns:
        List containing one Document with combined text
        
    Raises:
        ValueError: If document cannot be converted or has no text
    """
    print(f"[utils] docling_to_docs processing: {file_path}")
    
    try:
        converter = DocumentConverter()
        result = converter.convert(file_path)
    except Exception as e:
        print(f"[utils] ERROR: Docling conversion failed: {e}")
        raise ValueError(f"Failed to convert document {file_path}: {e}")
    
    print(f"[utils] Docling conversion result: {type(result)}")

    all_text = []
    page_info = []
    extraction_methods_tried = []

    if not result or not hasattr(result, 'document') or not result.document:
        print(f"[utils] ERROR: No document in conversion result")
        raise ValueError(f"Failed to convert document: {file_path}")

    doc = result.document
    print(f"[utils] Document object exists: {type(doc)}")
    
    # Method 1: Try to extract text from 'texts' attribute
    if hasattr(doc, 'texts') and doc.texts:
        extraction_methods_tried.append("texts attribute")
        print(f"[utils] Processing {len(doc.texts)} text elements")
        
        for i, text_element in enumerate(doc.texts):
            txt_content = getattr(text_element, 'text', None)
            if txt_content:
                txt = txt_content.strip()
                if txt:
                    all_text.append(txt)
                    # Extract page number if available
                    if hasattr(text_element, 'prov') and text_element.prov:
                        try:
                            page_no = getattr(text_element.prov[0], 'page_no', 1)
                            page_info.append(page_no)
                        except (IndexError, AttributeError):
                            page_info.append(1)
                    else:
                        page_info.append(1)
    
    # Method 2: Try to extract text from 'pages' attribute
    if not all_text and hasattr(doc, 'pages') and doc.pages:
        extraction_methods_tried.append("pages attribute")
        print(f"[utils] Processing {len(doc.pages)} pages")
        
        for i, page in enumerate(doc.pages):
            page_texts = []
            if hasattr(page, 'blocks'):
                for block in page.blocks:
                    txt = getattr(block, "text", "").strip()
                    if txt:
                        page_texts.append(txt)
            
            if page_texts:
                page_content = "\n".join(page_texts)
                all_text.append(page_content)
                page_info.append(getattr(page, "number", i + 1))
    
    # Method 3: Fallback to export_to_markdown
    if not all_text and hasattr(doc, 'export_to_markdown'):
        extraction_methods_tried.append("export_to_markdown method")
        print(f"[utils] Attempting export_to_markdown fallback")
        
        try:
            markdown_text = doc.export_to_markdown()
            if markdown_text and markdown_text.strip():
                all_text.append(markdown_text.strip())
                page_info.append(1)
        except Exception as e:
            print(f"[utils] Failed to export to markdown: {e}")

    # Check if any text was extracted
    if not all_text:
        available_attrs = [attr for attr in dir(doc) if not attr.startswith('_')]
        error_msg = (
            f"No text content extracted from document: {file_path}\n"
            f"Extraction methods tried: {', '.join(extraction_methods_tried)}\n"
            f"Document type: {type(doc).__name__}\n"
            f"Available attributes: {', '.join(available_attrs[:10])}..."
        )
        print(f"[utils] ERROR: {error_msg}")
        raise ValueError(error_msg)

    print(f"[utils] Total text segments collected: {len(all_text)}")
    combined = "\n\n".join(all_text)
    print(f"[utils] Combined text length: {len(combined)}")
    print(f"[utils] Combined text preview: {combined[:200]}...")
    
    document = Document(
        page_content=combined,
        metadata={
            "file": os.path.basename(file_path),
            "file_path": file_path,
            "total_pages": len(set(page_info)) if page_info else 1,
            "pages": ",".join(map(str, sorted(set(page_info)))) if page_info else "1",
            "extraction_method": extraction_methods_tried[0] if extraction_methods_tried else "unknown"
        }
    )
    
    print(f"[utils] Created Document with page_content length: {len(document.page_content)}")
    return [document]


# --- Other Loaders ---
def csv_to_docs(file_path: str, rows_per_doc: int = CSV_ROWS_PER_DOC) -> List[Document]:
    """
    Load CSV file as Documents, batching rows to avoid memory issues.
    
    Args:
        file_path: Path to CSV file
        rows_per_doc: Number of rows to combine into one document
        
    Returns:
        List of Documents, each containing multiple rows
    """
    try:
        df = pd.read_csv(file_path, encoding="utf-8")
        print(f"[utils] CSV loaded: {len(df)} rows, {len(df.columns)} columns")
        
        if df.empty:
            raise ValueError(f"CSV file is empty: {file_path}")
        
        docs = []
        
        # Batch rows together to reduce memory usage
        for start_idx in range(0, len(df), rows_per_doc):
            end_idx = min(start_idx + rows_per_doc, len(df))
            batch_rows = df.iloc[start_idx:end_idx]
            
            # Create content with headers
            content_lines = []
            for _, row in batch_rows.iterrows():
                row_content = " | ".join(str(v) for v in row.values)
                content_lines.append(row_content)
            
            content = "\n".join(content_lines)
            
            docs.append(Document(
                page_content=content,
                metadata={
                    "file": os.path.basename(file_path),
                    "file_path": file_path,
                    "rows": f"{start_idx + 1}-{end_idx}",
                    "total_rows": len(df),
                    "columns": list(df.columns)
                }
            ))
        
        print(f"[utils] CSV converted to {len(docs)} documents")
        return docs
        
    except Exception as e:
        print(f"[utils] ERROR loading CSV: {e}")
        raise


def xlsx_to_docs(file_path: str, rows_per_doc: int = CSV_ROWS_PER_DOC) -> List[Document]:
    """
    Load Excel file as Documents, batching rows to avoid memory issues.
    
    Args:
        file_path: Path to Excel file
        rows_per_doc: Number of rows to combine into one document
        
    Returns:
        List of Documents, each containing multiple rows
    """
    try:
        df = pd.read_excel(file_path)
        print(f"[utils] Excel loaded: {len(df)} rows, {len(df.columns)} columns")
        
        if df.empty:
            raise ValueError(f"Excel file is empty: {file_path}")
        
        docs = []
        
        # Batch rows together
        for start_idx in range(0, len(df), rows_per_doc):
            end_idx = min(start_idx + rows_per_doc, len(df))
            batch_rows = df.iloc[start_idx:end_idx]
            
            content_lines = []
            for _, row in batch_rows.iterrows():
                row_content = " | ".join(str(v) for v in row.values)
                content_lines.append(row_content)
            
            content = "\n".join(content_lines)
            
            docs.append(Document(
                page_content=content,
                metadata={
                    "file": os.path.basename(file_path),
                    "file_path": file_path,
                    "rows": f"{start_idx + 1}-{end_idx}",
                    "total_rows": len(df),
                    "columns": list(df.columns)
                }
            ))
        
        print(f"[utils] Excel converted to {len(docs)} documents")
        return docs
        
    except Exception as e:
        print(f"[utils] ERROR loading Excel: {e}")
        raise


def txt_to_docs(file_path: str) -> List[Document]:
    """
    Load text file as Document.
    
    Args:
        file_path: Path to text file
        
    Returns:
        List containing one Document with file content
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
        
        if not text.strip():
            raise ValueError(f"Text file is empty: {file_path}")
        
        print(f"[utils] Text file loaded: {len(text)} characters")
        
        return [Document(
            page_content=text,
            metadata={
                "file": os.path.basename(file_path),
                "file_path": file_path,
                "char_count": len(text)
            }
        )]
    except Exception as e:
        print(f"[utils] ERROR loading text file: {e}")
        raise


# --- Dispatcher ---
def get_loader(file_path: str) -> List[Document]:
    """
    Load document based on file extension.
    
    Args:
        file_path: Path to document file
        
    Returns:
        List of Document objects
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file type is unsupported or file is too large
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Check file size
    file_size = os.path.getsize(file_path)
    max_size = MAX_FILE_SIZE_MB * 1024 * 1024
    
    if file_size > max_size:
        raise ValueError(
            f"File too large: {file_size / 1024 / 1024:.1f}MB "
            f"(max: {MAX_FILE_SIZE_MB}MB)"
        )
    
    print(f"[utils] Loading file: {file_path} ({file_size / 1024:.1f}KB)")
    
    ext = os.path.splitext(file_path)[1].lower()
    
    loaders = {
        ".pdf": docling_to_docs,
        ".docx": docling_to_docs,
        ".pptx": docling_to_docs,
        ".md": docling_to_docs,
        ".csv": csv_to_docs,
        ".xlsx": xlsx_to_docs,
        ".txt": txt_to_docs,
    }
    
    loader = loaders.get(ext)
    if not loader:
        supported = ", ".join(sorted(loaders.keys()))
        raise ValueError(f"Unsupported file type: {ext}. Supported types: {supported}")
    
    return loader(file_path)


# --- MCP Server ---

def load_and_split(
    file_path: str, 
    chunk_size: int = 500, 
    chunk_overlap: int = 50
) -> List[Dict[str, Any]]:
    """
    Load a document and split it into chunks.
    
    Args:
        file_path: Path to the document file
        chunk_size: Maximum size of each chunk (default: 500)
        chunk_overlap: Number of characters to overlap between chunks (default: 50)
        
    Returns:
        List of dictionaries containing page_content and metadata
        
    Raises:
        ValueError: If parameters are invalid or file cannot be processed
        FileNotFoundError: If file doesn't exist
    """
    print(f"[MCP Tool] load_and_split called")
    print(f"[MCP Tool] file_path: {file_path}")
    print(f"[MCP Tool] chunk_size: {chunk_size}, chunk_overlap: {chunk_overlap}")
    
    try:
        # Load documents
        docs = get_loader(file_path)
        print(f"[MCP Tool] Loaded {len(docs)} documents")
        
        # Split into chunks
        chunks = []
        for doc_idx, doc in enumerate(docs):
            print(f"[MCP Tool] Processing document {doc_idx + 1}/{len(docs)}")
            
            text_chunks = simple_chunk_text(doc.page_content, chunk_size, chunk_overlap)
            print(f"[MCP Tool] Created {len(text_chunks)} chunks from document")
            
            for j, chunk in enumerate(text_chunks):
                metadata = {
                    **doc.metadata,
                    "chunk_id": j + 1,
                    "total_chunks": len(text_chunks),
                    "original_doc_length": len(doc.page_content),
                    "doc_index": doc_idx
                }
                chunks.append({
                    "page_content": chunk,
                    "metadata": metadata
                })
        
        print(f"[MCP Tool] Successfully returning {len(chunks)} total chunks")
        return chunks
        
    except Exception as e:
        print(f"[MCP Tool] ERROR: {e}")
        import traceback
        traceback.print_exc()
        # Re-raise with more context
        raise ValueError(f"Failed to load and split document: {str(e)}")