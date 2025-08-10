from typing import List

from langchain.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings

from app.config import PERSIST_DIR, EMBEDDING_MODEL


embedding_function = HuggingFaceEmbeddings(
    model_name=EMBEDDING_MODEL
)
vectorstore = Chroma(persist_directory=PERSIST_DIR, embedding_function=embedding_function)


