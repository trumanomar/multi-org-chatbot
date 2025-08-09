import os
from langchain.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
import pandas as pd
def get_loader(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        return PyPDFLoader(file_path)
    elif ext == ".docx":
        return Docx2txtLoader(file_path)
    elif ext == ".txt":
        return TextLoader(file_path)
    elif ext == ".csv":
        return pd.read_csv(file_path, encoding="utf-8")
    elif ext==".md":
        return TextLoader(file_path, encoding="utf-8")
    else:
        raise ValueError(f"Unsupported file type: {ext}")

def load_and_split(file_path):
    loader = get_loader(file_path)
    docs = loader.load()
    return splitter.split_documents(docs)
