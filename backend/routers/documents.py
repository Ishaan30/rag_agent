"""
Documents Router
Exposes:
  POST /api/documents/upload  — accept a PDF or text file and run RAG ingestion
  GET  /api/documents/status  — check whether a document is loaded
"""

import os
import tempfile

from fastapi import APIRouter, UploadFile, File, HTTPException

from services.rag import ingest_document
import state

router = APIRouter()


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Accept a PDF or .txt file, save it temporarily, and run RAG ingestion.
    Returns stats about the ingestion (chunk count, page count, etc.).
    """
    allowed_types = {
        "application/pdf",
        "text/plain",
        "text/markdown",
    }

    # Basic content-type validation (also validate extension below)
   # Replace this strict check:

    print(f"Received: {file.filename}, content_type: {file.content_type}")
    # With this — trust the extension, not the content-type:
    if not file.filename.endswith((".pdf", ".txt", ".md")):
        raise HTTPException(
            status_code=400,
            detail="Only PDF and plain text (.txt / .md) files are supported.",
        )

    # Write upload to a temp file so loaders can read from disk
    suffix = os.path.splitext(file.filename)[-1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = await ingest_document(tmp_path, file.filename)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        print(f"Ingestion error: {e}") 
        raise HTTPException(status_code=500, detail=str(e))
      
    finally:
        os.unlink(tmp_path)   # Always clean up the temp file

    return result


@router.get("/status")
async def document_status():
    """Return whether a document is currently loaded in the vector store."""
    loaded = state.vector_store is not None
    return {"document_loaded": loaded}