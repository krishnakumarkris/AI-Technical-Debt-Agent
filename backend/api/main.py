import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Optional

# backend/ must be on sys.path so flat imports (scanner.*, debt_analyzer.*) resolve
_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from scanner.scanner_service import ScannerService

app = FastAPI(
    title="AI Technical Debt Agent API",
    description="API for scanning Java projects and calculating technical debt metrics",
    version="1.0.0"
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Scanner Service
scanner_service = ScannerService()

# Find the absolute path of backend directory
BACKEND_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BACKEND_DIR / "static"
UPLOAD_TEMP_DIR = BACKEND_DIR / "scanner" / "uploads" / "temp"

# Create directories if they do not exist
STATIC_DIR.mkdir(exist_ok=True)
UPLOAD_TEMP_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/api/sample")
def scan_sample():
    """
    Scans the pre-packaged SampleProject.
    """
    sample_path = BACKEND_DIR / "scanner" / "uploads" / "SampleProject"
    if not sample_path.exists():
        raise HTTPException(
            status_code=404, 
            detail=f"Sample project not found at {sample_path}"
        )
    
    try:
        result = scanner_service.scan(str(sample_path), save_output=True)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/scan-path")
def scan_path(path: str = Query(..., description="Absolute path to the project directory to scan")):
    """
    Scans a local directory on the server.
    """
    target_path = Path(path)
    if not target_path.exists():
        raise HTTPException(
            status_code=400,
            detail=f"The specified path does not exist on the server: {path}"
        )
    
    try:
        result = scanner_service.scan(str(target_path), save_output=True)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/scan-upload")
async def scan_upload(file: UploadFile = File(..., description="ZIP archive of the Java project")):
    """
    Upload a project ZIP file, extract it, scan it, and clean up.
    """
    if not file.filename.endswith(".zip"):
        raise HTTPException(
            status_code=400,
            detail="Only ZIP file uploads are supported."
        )

    # Generate a unique temp directory for extraction
    temp_extract_dir = Path(tempfile.mkdtemp(dir=str(UPLOAD_TEMP_DIR)))
    temp_zip_path = temp_extract_dir / file.filename

    try:
        # Save ZIP file
        with open(temp_zip_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # Extract ZIP file
        with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_extract_dir)

        # Remove the ZIP archive itself so it doesn't get scanned
        temp_zip_path.unlink()

        # Find the root of the project inside the extraction folder.
        # Sometimes ZIP archives wrap everything in a single root folder.
        scan_target = temp_extract_dir
        subdirs = [d for d in temp_extract_dir.iterdir() if d.is_dir()]
        
        # If there's a single top-level folder inside the zip, scan that instead
        if len(subdirs) == 1 and not any(f.is_file() for f in temp_extract_dir.iterdir()):
            scan_target = subdirs[0]

        # Scan the project
        result = scanner_service.scan(str(scan_target), save_output=True)
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # Background cleanup or immediate cleanup of the uploaded source files.
        # Let's delete the extracted directory to avoid storage leaks.
        try:
            shutil.rmtree(temp_extract_dir)
        except Exception:
            pass


@app.get("/")
def read_root():
    """
    Serves the main application page.
    """
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        return {"message": "Welcome to AI Technical Debt Agent. Frontend not created yet."}
    return FileResponse(index_file)


# Mount static assets directory
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
