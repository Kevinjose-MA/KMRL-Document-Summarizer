import os
import shutil
import time
from datetime import datetime
from typing import Optional, List

# FastAPI Imports
from fastapi import FastAPI, UploadFile, File, APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from starlette.middleware.cors import CORSMiddleware 

# MongoDB/BSON Imports
from bson.objectid import ObjectId

# Internal Module Imports - FIX: Using relative imports from the 'scripts' subdirectory
from .scripts import config
from .scripts import utils
from .scripts import database_connection as db # Imported from scripts/ and aliased to 'db'
from .scripts import ingestion
from .scripts import extraction
from .scripts import document_summarizer


# =======================================================
# CONFIGURATION & INITIALIZATION
# =======================================================

# Use configurations from config.py
# NOTE: config.py is now expected to be in app/scripts/config.py
RAW_FOLDER = config.RAW_DIR
PROCESSED_FOLDER = config.PROCESSED_DIR
SUMMARY_FOLDER = config.SUMMARIES_DIR

# Ensure folders exist
os.makedirs(RAW_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)
os.makedirs(SUMMARY_FOLDER, exist_ok=True)

# FastAPI app initialization
app = FastAPI(title="KMRL Document Summarizer")
router = APIRouter(prefix="/api") 

# --- CORS Configuration ---
origins = ["*"] # Allowing all origins for development flexibility

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------
# Pydantic Models
# ---------------------------
class DocumentData(BaseModel):
    title: str
    url: str
    summary: str
    uploadedBy: str
    uploadedAt: str

class URLIngest(BaseModel):
    url: str
    filename: str 

# =======================================================
# ASYNC DATABASE WRAPPERS (Using database_connection.py's client)
# =======================================================

# NOTE: Assumes 'db' alias refers to the database_connection module
SUMMARY_COLLECTION = db.db.summaries 

async def get_all_documents():
    """Retrieves all document records from the database."""
    try:
        documents = await SUMMARY_COLLECTION.find().to_list(1000)
        # Convert ObjectId to string for JSON serialization
        for doc in documents:
            if '_id' in doc:
                doc['_id'] = str(doc.pop('_id')) 
        return documents
    except Exception as e:
        print(f"DB Read Error: {e}")
        raise HTTPException(status_code=500, detail="Database connection error on fetch.")

async def save_document_to_db(doc_data: DocumentData, summary_file_path: str):
    """Saves a new summarized document record to the database."""
    doc_dict = doc_data.dict()
    doc_dict['uploadedAt'] = datetime.utcnow().isoformat()
    doc_dict['summaryFilePath'] = summary_file_path # Store the path to the summary file
    
    try:
        result = await SUMMARY_COLLECTION.insert_one(doc_dict)
        return {"message": "Document saved successfully.", "_id": str(result.inserted_id)}
    except Exception as e:
        print(f"DB Save Error: {e}")
        raise HTTPException(status_code=500, detail="Database connection error on save.")

# =======================================================
# DOCUMENT API ENDPOINTS
# =======================================================

@router.get("/documents", response_model=List[dict])
async def get_documents_endpoint():
    """Endpoint for retrieving all documents."""
    return await get_all_documents()

@router.post("/documents")
async def create_document_endpoint(doc_data: DocumentData):
    """Placeholder endpoint for saving pre-summarized documents (not used in current flow)."""
    return {"message": "Use /upload/ or /ingest_url/ to create summaries."}


# =======================================================
# INGESTION ENDPOINTS (Triggering LLM)
# =======================================================

@app.post("/upload/")
async def upload_file_endpoint(file: UploadFile = File(...)):
    """
    Uploads a local file, processes, summarizes (via LLM), and saves the record.
    """
    base_filename, ext = os.path.splitext(file.filename)
    raw_path = os.path.join(RAW_FOLDER, file.filename)
    
    # 1. Save raw file locally
    try:
        file.file.seek(0) 
        with open(raw_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {str(e)}")

    # 2. Summarize the document (This triggers the LLM logic in document_summarizer.py)
    try:
        summary_text = document_summarizer.summarize_document(raw_path) 
    except Exception as e:
        print(f"Summarization failed for {file.filename}: {e}")
        if os.path.exists(raw_path):
            os.remove(raw_path)
        raise HTTPException(status_code=500, detail=f"Failed to generate summary: {str(e)}")

    # 3. Save the summary to a file (for download)
    summary_file_path = document_summarizer.save_summary(summary_text, base_filename, SUMMARY_FOLDER)
    
    # 4. Save metadata to the database
    doc_data = DocumentData(
        title=base_filename,
        url=f"local://{file.filename}",
        summary=summary_text,
        uploadedBy="authenticated_user@kmrl.com", 
        uploadedAt=datetime.utcnow().isoformat()
    )
    db_result = await save_document_to_db(doc_data, summary_file_path)

    return {
        "original_filename": file.filename,
        "summary_content": summary_text,
        "db_id": db_result.get('_id'),
        "summary_download_name": os.path.basename(summary_file_path)
    }


@app.post("/ingest_url/")
async def ingest_url_endpoint(data: URLIngest):
    """
    Fetches a document from a URL, processes, summarizes (via LLM), and saves the record.
    """
    url = data.url
    base_filename = data.filename

    # 1. Fetch content from URL and save to raw folder
    raw_path_or_error = ingestion.save_file_from_url(url)
    
    if isinstance(raw_path_or_error, str) and raw_path_or_error.startswith("Error"):
        raise HTTPException(status_code=400, detail=raw_path_or_error)
        
    raw_path = raw_path_or_error

    # 2. Summarize the document (This triggers the LLM logic in document_summarizer.py)
    try:
        summary_text = document_summarizer.summarize_document(raw_path)
    except Exception as e:
        print(f"Summarization failed for {base_filename}: {e}")
        if os.path.exists(raw_path):
            os.remove(raw_path)
        raise HTTPException(status_code=500, detail=f"Failed to generate summary: {str(e)}")

    # 3. Save the summary to a file (for download)
    summary_file_path = document_summarizer.save_summary(summary_text, base_filename, SUMMARY_FOLDER)

    # 4. Save metadata to the database
    doc_data = DocumentData(
        title=base_filename,
        url=url,
        summary=summary_text,
        uploadedBy="authenticated_user@kmrl.com",
        uploadedAt=datetime.utcnow().isoformat()
    )
    db_result = await save_document_to_db(doc_data, summary_file_path)
    
    return {
        "original_filename": base_filename,
        "summary_content": summary_text,
        "db_id": db_result.get('_id'),
        "summary_download_name": os.path.basename(summary_file_path)
    }

# ---------------------------
# Download summary
# ---------------------------
@app.get("/download_summary/{filename}")
def download_summary(filename: str):
    """
    Download a summary file from SUMMARY_FOLDER.
    """
    summary_path = os.path.join(SUMMARY_FOLDER, filename)
    if not os.path.exists(summary_path):
        return JSONResponse(status_code=404, content={"error": "Summary file not found"})
    return FileResponse(summary_path, filename=filename, media_type="text/plain")

# --------------------------
# Bulk ingestion endpoint
# --------------------------
@app.post("/ingest_all/")
async def ingest_all_endpoint():
    """
    Ingest all raw files, process, summarize, and save records.
    """
    return {"message": "Bulk ingestion request received. Processing logic needs implementation."}


# CRITICAL: Include the router so /api/documents routes are live
app.include_router(router)

# ---------------------------
# Root endpoint
# ---------------------------
@app.get("/")
def root():
    return {"message": "KMRL Document Summarizer API is running"}
