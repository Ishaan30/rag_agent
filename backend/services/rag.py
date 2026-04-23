import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

import google.generativeai as genai
from langchain.embeddings.base import Embeddings
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS

import state

load_dotenv()

# ─── Config ───────────────────────────────────────────────────────────────────
CHUNK_SIZE = 300
CHUNK_OVERLAP = 80
# ─── Gemini REST Embeddings (no gRPC) ─────────────────────────────────────────
class GeminiRESTEmbeddings(Embeddings):
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [
            genai.embed_content(
                model="models/gemini-embedding-001",
                content=t,
                task_type="retrieval_document"
            )["embedding"]
            for t in texts
        ]

    def embed_query(self, text: str) -> List[float]:
        return genai.embed_content(
            model="models/gemini-embedding-001",
            content=text,
            task_type="retrieval_query"
        )["embedding"]

def _get_embeddings() -> GeminiRESTEmbeddings:
    return GeminiRESTEmbeddings(api_key=os.environ["GOOGLE_API_KEY"])

# ─── Public Interface ─────────────────────────────────────────────────────────
async def ingest_document(file_path: str, filename: str) -> dict:
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        loader = PyPDFLoader(file_path)
    elif ext in (".txt", ".md"):
        loader = TextLoader(file_path, encoding="utf-8")
    else:
        raise ValueError(f"Unsupported file type: {ext}")

    documents = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ".", " ", ""],
    )
    chunks = splitter.split_documents(documents)

    if not chunks:
        raise ValueError("The document appears to be empty after parsing.")

    embeddings = _get_embeddings()
    state.vector_store = FAISS.from_documents(documents=chunks, embedding=embeddings)

    return {
        "filename": filename,
        "pages": len(documents),
        "chunks": len(chunks),
        "message": f"Ingested '{filename}' — {len(chunks)} chunks ready for Q&A.",
    }