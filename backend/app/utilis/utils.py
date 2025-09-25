import os
import json
import pandas as pd
from langchain.docstore.document import Document
from docling.document_converter import DocumentConverter
from fastmcp import FastMCP

# --- Simple Chunker ---
def simple_chunk_text(text, chunk_size=500, chunk_overlap=50):
    print(f"[utils] simple_chunk_text called with text length: {len(text)}")
    print(f"[utils] chunk_size: {chunk_size}, chunk_overlap: {chunk_overlap}")
    
    if not text or not text.strip():
        print(f"[utils] WARNING: Empty or whitespace-only text provided")
        return []
    
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        stripped_chunk = chunk.strip()
        if stripped_chunk:  # Only add non-empty chunks
            chunks.append(stripped_chunk)
            print(f"[utils] Created chunk {len(chunks)}: length={len(stripped_chunk)}")
        start += chunk_size - chunk_overlap
    
    print(f"[utils] simple_chunk_text returning {len(chunks)} chunks")
    return chunks


# --- Docling Loader ---
def docling_to_docs(file_path):
    print(f"[utils] docling_to_docs processing: {file_path}")
    converter = DocumentConverter()
    result = converter.convert(file_path)
    
    print(f"[utils] Docling conversion result: {type(result)}")
    print(f"[utils] Has document: {hasattr(result, 'document') and result.document is not None}")

    all_text = []
    page_info = []

    if result.document:
        print(f"[utils] Document object exists")
        print(f"[utils] Has texts: {hasattr(result.document, 'texts')}")
        print(f"[utils] Has pages: {hasattr(result.document, 'pages')}")
        
        if hasattr(result.document, 'texts') and result.document.texts:
            print(f"[utils] Processing {len(result.document.texts)} text elements")
            for i, text_element in enumerate(result.document.texts):
                txt_content = getattr(text_element, 'text', None)
                print(f"[utils] Text element {i}: has text = {txt_content is not None}")
                if txt_content:
                    txt = txt_content.strip()
                    print(f"[utils] Text element {i}: length after strip = {len(txt)}")
                    if txt:
                        all_text.append(txt)
                        print(f"[utils] Added text: {txt[:100]}...")
                        if hasattr(text_element, 'prov') and text_element.prov:
                            try:
                                page_no = getattr(text_element.prov[0], 'page_no', 1)
                                page_info.append(page_no)
                            except Exception:
                                page_info.append(1)
                        
        elif hasattr(result.document, 'pages'):
            print(f"[utils] Processing {len(result.document.pages)} pages")
            for i, page in enumerate(result.document.pages):
                print(f"[utils] Page {i}: has blocks = {hasattr(page, 'blocks')}")
                page_texts = []
                if hasattr(page, 'blocks'):
                    print(f"[utils] Page {i}: {len(page.blocks)} blocks")
                    for j, block in enumerate(getattr(page, "blocks", [])):
                        txt = getattr(block, "text", "").strip()
                        print(f"[utils] Page {i}, Block {j}: text length = {len(txt)}")
                        if txt:
                            page_texts.append(txt)
                            print(f"[utils] Block text preview: {txt[:100]}...")
                if page_texts:
                    page_content = "\n".join(page_texts)
                    all_text.append(page_content)
                    print(f"[utils] Page {i}: combined text length = {len(page_content)}")
                    page_info.append(getattr(page, "number", len(page_info) + 1))
        else:
            print(f"[utils] WARNING: Document has neither texts nor pages attributes")
            # Try to access document content directly
            if hasattr(result.document, 'content'):
                print(f"[utils] Document has content attribute: {type(result.document.content)}")
            if hasattr(result.document, 'text'):
                print(f"[utils] Document has text attribute: {type(result.document.text)}")
    else:
        print(f"[utils] ERROR: No document in result")

    print(f"[utils] Total text segments collected: {len(all_text)}")
    combined = "\n\n".join(all_text)
    print(f"[utils] Combined text length: {len(combined)}")
    print(f"[utils] Combined text preview: {combined[:200]}...")
    
    doc = Document(
        page_content=combined,
        metadata={
            "file": file_path,
            "total_pages": len(set(page_info)) if page_info else 1,
            "pages": ",".join(map(str, sorted(set(page_info)))) if page_info else "1"
        }
    )
    
    print(f"[utils] Created Document with page_content length: {len(doc.page_content)}")
    return [doc]


# --- Other Loaders ---
def csv_to_docs(file_path):
    df = pd.read_csv(file_path, encoding="utf-8")
    return [Document(page_content=" | ".join(str(v) for v in row.values), metadata={"file": file_path})
            for _, row in df.iterrows()]

def xlsx_to_docs(file_path):
    df = pd.read_excel(file_path)
    return [Document(page_content=" | ".join(str(v) for v in row.values), metadata={"file": file_path})
            for _, row in df.iterrows()]

def txt_to_docs(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()
    return [Document(page_content=text, metadata={"file": file_path})]


# --- Dispatcher ---
def get_loader(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    if ext in [".pdf", ".docx", ".pptx", ".md"]:
        return docling_to_docs(file_path)
    elif ext == ".csv":
        return csv_to_docs(file_path)
    elif ext == ".xlsx":
        return xlsx_to_docs(file_path)
    elif ext == ".txt":
        return txt_to_docs(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")


# --- Core logic function (callable in Uploadroute.py) ---
def load_and_split_func(file_path: str, chunk_size: int = 500, chunk_overlap: int = 50):
    print(f"[utils] Starting load_and_split_func for: {file_path}")
    
    try:
        docs = get_loader(file_path)
        print(f"[utils] get_loader returned {len(docs)} documents")
        
        if docs:
            for i, doc in enumerate(docs):
                print(f"[utils] Doc {i}: content length = {len(doc.page_content)}")
                print(f"[utils] Doc {i}: content preview = {doc.page_content[:200]}...")
                print(f"[utils] Doc {i}: metadata = {doc.metadata}")
        
        chunks = []
        for doc in docs:
            print(f"[utils] Processing doc with content length: {len(doc.page_content)}")
            text_chunks = simple_chunk_text(doc.page_content, chunk_size, chunk_overlap)
            print(f"[utils] simple_chunk_text returned {len(text_chunks)} chunks")
            
            for j, chunk in enumerate(text_chunks):
                print(f"[utils] Processing chunk {j+1}: length = {len(chunk)}")
                # Return Document objects instead of dictionaries
                chunk_doc = Document(
                    page_content=chunk,
                    metadata={
                        **doc.metadata,
                        "chunk_id": j + 1,
                        "total_chunks": len(text_chunks),
                        "original_doc_length": len(doc.page_content),
                    }
                )
                chunks.append(chunk_doc)
        
        print(f"[utils] Final result: {len(chunks)} total chunks")
        return chunks
        
    except Exception as e:
        print(f"[utils] ERROR in load_and_split_func: {e}")
        import traceback
        traceback.print_exc()
        return []


# --- MCP Server ---
mcp = FastMCP("docling-mcp")

@mcp.tool()
def load_and_split(file_path: str, chunk_size: int = 500, chunk_overlap: int = 50):
    """
    Load a document with Docling/CSV/XLSX/TXT and return JSON-serializable chunks.
    """
    docs = get_loader(file_path)
    chunks = []
    for doc in docs:
        text_chunks = simple_chunk_text(doc.page_content, chunk_size, chunk_overlap)
        for j, chunk in enumerate(text_chunks):
            metadata = {
                **doc.metadata,
                "chunk_id": j + 1,
                "total_chunks": len(text_chunks),
                "original_doc_length": len(doc.page_content),
            }
            chunks.append({
                "content": chunk,
                "metadata": metadata
            })
    return chunks

if __name__ == "__main__":
    mcp.run()