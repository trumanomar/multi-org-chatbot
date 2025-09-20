import os
import pandas as pd
import json
from langchain.docstore.document import Document
from docling.document_converter import DocumentConverter
from llm_arabic_instruct_gen.processors.chunker import TextChunker


# --- Docling loader (for PDF, DOCX, PPTX, MD) ---
def docling_to_docs(file_path):
    converter = DocumentConverter()
    result = converter.convert(file_path)

    # ✅ اطبع الـ DOM كله (صفحات, بلوكات, إلخ)
    if result.document:
        dom_dict = result.document.model_dump()
        dom_json = json.dumps(dom_dict, ensure_ascii=False, indent=2)
        print("========= DOC DOM =========")
        print(dom_json)
        print("===========================")
    else:
        print("⚠️ No document object found")
        return []

    # ✅ Extract text from the texts array in the document
    all_text = []
    page_info = []
    
    if hasattr(result, "document") and result.document:
        # Method 1: Try to get text from the 'texts' array (more reliable for Arabic)
        if hasattr(result.document, 'texts') and result.document.texts:
            print(f"[DEBUG] Found {len(result.document.texts)} text elements")
            for text_element in result.document.texts:
                if hasattr(text_element, 'text') and text_element.text:
                    text_content = text_element.text.strip()
                    if text_content:
                        all_text.append(text_content)
                        # Try to get page info from prov
                        if hasattr(text_element, 'prov') and text_element.prov:
                            try:
                                page_no = getattr(text_element.prov[0], 'page_no', 1)
                                if page_no not in page_info:
                                    page_info.append(page_no)
                            except (IndexError, AttributeError):
                                # If we can't get page info, default to page 1
                                if 1 not in page_info:
                                    page_info.append(1)
        
        # Method 2: Fallback to pages/blocks method if no texts found
        elif hasattr(result.document, 'pages') and result.document.pages:
            print("[DEBUG] Using pages/blocks method as fallback")
            for page in result.document.pages:
                page_texts = []
                if hasattr(page, "blocks") and page.blocks:
                    for block in page.blocks:
                        text = getattr(block, "text", "").strip()
                        if text:
                            page_texts.append(text)
                
                if page_texts:
                    page_text = "\n".join(page_texts)
                    all_text.append(page_text)
                    page_info.append(getattr(page, "number", len(page_info) + 1))
    
    print(f"[DEBUG] Extracted {len(all_text)} text segments")
    if all_text:
        # Preview first few characters of extracted text
        combined_text = "\n\n".join(all_text)
        print(f"[DEBUG] Combined text length: {len(combined_text)} characters")
        print(f"[DEBUG] Text preview: {combined_text[:200]}...")
        
        return [Document(
            page_content=combined_text,
            metadata={
                "file": file_path,
                "total_pages": len(set(page_info)) if page_info else 1,
                "pages": ",".join(map(str, sorted(list(set(page_info))))) if page_info else "1"  # Convert list to string
            }
        )]
    
    print("⚠️ No text content extracted")
    return []


# --- Alternative: Keep page-level documents ---
def docling_to_docs_by_page(file_path):
    """Alternative approach: Create one document per page"""
    converter = DocumentConverter()
    result = converter.convert(file_path)

    docs = []
    if hasattr(result, "document") and result.document:
        for page in result.document.pages:
            if hasattr(page, "blocks"):
                page_texts = []
                for block in page.blocks:
                    text = getattr(block, "text", "").strip()
                    if text:
                        page_texts.append(text)
                
                if page_texts:
                    page_text = "\n".join(page_texts)
                    docs.append(
                        Document(
                            page_content=page_text,
                            metadata={
                                "file": file_path,
                                "page": getattr(page, "number", None),
                                "total_pages": len(result.document.pages) if hasattr(result.document, 'pages') else 1
                            }
                        )
                    )
    return docs


# --- Custom loaders for tabular & plain text ---
def csv_to_docs(file_path):
    df = pd.read_csv(file_path, encoding="utf-8")
    docs = []
    for _, row in df.iterrows():
        text = " | ".join(str(v) for v in row.values)
        docs.append(Document(page_content=text, metadata={"file": file_path}))
    return docs

def xlsx_to_docs(file_path):
    df = pd.read_excel(file_path)
    docs = []
    for _, row in df.iterrows():
        text = " | ".join(str(v) for v in row.values)
        docs.append(Document(page_content=text, metadata={"file": file_path}))
    return docs

def txt_to_docs(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()
    return [Document(page_content=text, metadata={"file": file_path})]


# --- Dispatcher ---
def get_loader(file_path, use_page_level=False):
    """
    Args:
        file_path: Path to the file
        use_page_level: If True, create separate documents per page for PDFs/DOCX
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext in [".pdf", ".docx", ".pptx", ".md"]:
        if use_page_level:
            return docling_to_docs_by_page(file_path)
        else:
            return docling_to_docs(file_path)
    elif ext == ".csv":
        return csv_to_docs(file_path)
    elif ext == ".xlsx":
        return xlsx_to_docs(file_path)
    elif ext == ".txt":
        return txt_to_docs(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")


# --- Loader + Chunker ---
def load_and_split(file_path, chunk_size=500, chunk_overlap=50, use_page_level=False):
    """
    Args:
        file_path: Path to the file
        chunk_size: Size of each chunk
        chunk_overlap: Overlap between chunks
        use_page_level: For PDFs/DOCX, whether to chunk per page or entire document
    """
    docs = get_loader(file_path, use_page_level=use_page_level)
    
    if not docs:
        print("[ERROR] No documents loaded!")
        return []
    
    chunker = TextChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    chunks = []
    for i, doc in enumerate(docs):
        if not doc.page_content or not doc.page_content.strip():
            print(f"[DEBUG] Document {i+1} is empty, skipping")
            continue

        print(f"[DEBUG] Document {i+1} length: {len(doc.page_content)} characters")
        print(f"[DEBUG] Document {i+1} preview: {doc.page_content[:100]}...")
        
        try:
            # ✅ Always try to chunk, regardless of size
            text_chunks = chunker.chunk_text(doc.page_content)
            print(f"[DEBUG] Chunker returned {len(text_chunks) if text_chunks else 0} chunks")
            
            # ✅ If no chunks created but document has content, keep as single chunk
            if not text_chunks and doc.page_content.strip():
                text_chunks = [doc.page_content.strip()]
                print(f"[DEBUG] Document {i+1} kept as single chunk (smaller than chunk_size or chunker failed)")

            print(f"[DEBUG] Document {i+1} → {len(text_chunks)} final chunks")

            for j, chunk in enumerate(text_chunks):
                if chunk and chunk.strip():  # Only add non-empty chunks
                    chunk_metadata = doc.metadata.copy()
                    chunk_metadata['chunk_id'] = j + 1
                    chunk_metadata['total_chunks'] = len(text_chunks)
                    chunk_metadata['original_doc_length'] = len(doc.page_content)
                    chunks.append(Document(page_content=chunk.strip(), metadata=chunk_metadata))
                else:
                    print(f"[DEBUG] Skipping empty chunk {j+1} from document {i+1}")
                    
        except Exception as e:
            print(f"[ERROR] Failed to chunk document {i+1}: {str(e)}")
            # Fallback: treat entire document as one chunk
            chunk_metadata = doc.metadata.copy()
            chunk_metadata['chunk_id'] = 1
            chunk_metadata['total_chunks'] = 1
            chunk_metadata['original_doc_length'] = len(doc.page_content)
            chunk_metadata['chunking_error'] = str(e)
            chunks.append(Document(page_content=doc.page_content.strip(), metadata=chunk_metadata))

    print(f"[DEBUG] Total chunks created: {len(chunks)}")
    if chunks:
        print(f"[DEBUG] First chunk preview: {chunks[0].page_content[:100]}...")
    return chunks