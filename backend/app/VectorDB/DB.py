from typing import List
import os
from tempfile import NamedTemporaryFile
from sentence_transformers import SentenceTransformer

from langchain.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import pandas as pd
from app.config import PERSIST_DIR, EMBEDDING_MODEL


embedding_function = HuggingFaceEmbeddings(
    model_name=EMBEDDING_MODEL
)
#HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
vectorstore = Chroma(persist_directory=PERSIST_DIR, embedding_function=embedding_function)
