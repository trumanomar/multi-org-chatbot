import os
from langchain.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
import pandas as pd

splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)

def csv_to_docs(file_path):
    df = pd.read_csv(file_path, encoding="utf-8")
    docs = []
    for _, row in df.iterrows():
        # Join all values in the row into a single string
        text = " | ".join(str(v) for v in row.values)
        docs.append(Document(page_content=text))
    return docs

def xlsx_to_docs(file_path):
    df = pd.read_excel(file_path)
    docs = []
    for _, row in df.iterrows():
        text = " | ".join(str(v) for v in row.values)
        docs.append(Document(page_content=text))
    return docs

def get_loader(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        return PyPDFLoader(file_path)
    elif ext == ".docx":
        return Docx2txtLoader(file_path)
    elif ext == ".txt":
        return TextLoader(file_path)
    elif ext == ".csv":
        return csv_to_docs(file_path)
    elif ext == ".xlsx":
        return xlsx_to_docs(file_path)
    elif ext==".md":
        return TextLoader(file_path, encoding="utf-8")
    else:
        raise ValueError(f"Unsupported file type: {ext}")

def load_and_split(file_path):
    loader = get_loader(file_path)
    if isinstance(loader, list):
        # If the loader returns a list (like csv_to_docs or xlsx_to_docs)
        docs = loader
    else:   
        docs = loader.load()
    return splitter.split_documents(docs)
