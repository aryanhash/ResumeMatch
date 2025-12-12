# Cline Prompt: FastAPI Orchestrator Endpoint

## Objective
Generate a FastAPI application that orchestrates the resume processing pipeline with **proper security and error handling**.

---

## Critical Issues to Fix

### Issue #1: No File Validation
```python
# ❌ WRONG - accepts any file
file_path = f"/tmp/{resume.filename}"
with open(file_path, "wb") as f:
    f.write(await resume.read())

# ✅ CORRECT - validate before saving
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

def validate_file(file: UploadFile) -> None:
    # Check extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Invalid file type. Allowed: {ALLOWED_EXTENSIONS}")
    
    # Check size (read first chunk)
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)
    if size > MAX_FILE_SIZE:
        raise HTTPException(413, f"File too large. Max: {MAX_FILE_SIZE/1024/1024}MB")
```

### Issue #2: No JD Text Validation
```python
# ❌ WRONG - accepts anything
job_description: str = Form(...)

# ✅ CORRECT - validate length and content
MIN_JD_LENGTH = 100
MAX_JD_LENGTH = 15000

def validate_jd(jd_text: str) -> str:
    if len(jd_text) < MIN_JD_LENGTH:
        raise HTTPException(422, "Job description too short (min 100 chars)")
    if len(jd_text) > MAX_JD_LENGTH:
        raise HTTPException(422, "Job description too long (max 15000 chars)")
    # Check it's actual text
    if jd_text.startswith(('%PDF', 'PK')):
        raise HTTPException(422, "Job description appears to be binary, not text")
    return jd_text
```

### Issue #3: No Cleanup
```python
# ❌ WRONG - files accumulate forever
file_path = f"/tmp/{workflow_id}_{resume.filename}"
# No cleanup!

# ✅ CORRECT - schedule cleanup
async def cleanup_temp_file(file_path: str, delay_hours: int = 24):
    """Delete temp file after processing."""
    await asyncio.sleep(delay_hours * 3600)
    if os.path.exists(file_path):
        os.remove(file_path)

# In endpoint:
background_tasks.add_task(cleanup_temp_file, file_path, 24)
```

---

## Requirements

Write a FastAPI application with:

### 1. Application Configuration

```python
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import time
import os
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# File limits
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
MIN_JD_LENGTH = 100
MAX_JD_LENGTH = 15000

app = FastAPI(
    title="AutoApply AI",
    description="AI-powered resume optimization and ATS scoring",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 2. Request Logging Middleware

```python
class RequestLoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start_time = time.time()
        request_id = str(uuid.uuid4())[:8]
        
        logger.info(f"[{request_id}] {request.method} {request.url.path}")
        
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            logger.info(f"[{request_id}] {response.status_code} ({duration:.2f}s)")
            return response
        except Exception as e:
            logger.error(f"[{request_id}] Error: {str(e)}")
            raise

app.add_middleware(RequestLoggerMiddleware)
```

### 3. File Validation Utilities

```python
def validate_resume_file(file: UploadFile) -> None:
    """Validate uploaded resume file."""
    if not file.filename:
        raise HTTPException(400, "No filename provided")
    
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            400, 
            f"Invalid file type '{ext}'. Allowed: PDF, DOCX, TXT"
        )
    
    # Check file size
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)
    
    if size > MAX_FILE_SIZE:
        raise HTTPException(
            413, 
            f"File too large ({size/1024/1024:.1f}MB). Max: 5MB"
        )
    
    if size == 0:
        raise HTTPException(400, "Empty file uploaded")


def validate_jd_text(jd: str) -> str:
    """Validate job description text."""
    if not jd or not jd.strip():
        raise HTTPException(422, "Job description is required")
    
    jd = jd.strip()
    
    if len(jd) < MIN_JD_LENGTH:
        raise HTTPException(
            422, 
            f"Job description too short ({len(jd)} chars). Min: {MIN_JD_LENGTH}"
        )
    
    if len(jd) > MAX_JD_LENGTH:
        raise HTTPException(
            422, 
            f"Job description too long ({len(jd)} chars). Max: {MAX_JD_LENGTH}"
        )
    
    # Check for binary content
    if jd.startswith(('%PDF', 'PK', '\x00')):
        raise HTTPException(422, "Invalid text format (appears to be binary)")
    
    return jd
```

### 4. Main Processing Endpoint

```python
@app.post("/process")
async def process_resume(
    resume: UploadFile = File(..., description="Resume file (PDF, DOCX, or TXT)"),
    job_description: str = Form(..., description="Job description text"),
    background_tasks: BackgroundTasks
):
    """
    Process resume and job description.
    
    - Validates inputs
    - Extracts text from resume
    - Runs full analysis pipeline
    - Returns comprehensive results
    
    Returns:
        JSON with ATS score, gap analysis, rewritten resume, cover letter
    """
    request_id = str(uuid.uuid4())
    logger.info(f"[{request_id}] Processing: {resume.filename}")
    
    try:
        # Validate inputs
        validate_resume_file(resume)
        jd_text = validate_jd_text(job_description)
        
        # Read and extract text
        file_content = await resume.read()
        resume_text = extract_text_from_file(file_content, resume.filename)
        
        if len(resume_text) < 50:
            raise HTTPException(422, "Could not extract meaningful text from resume")
        
        # Run pipeline
        result = await run_pipeline(resume_text, jd_text)
        
        # Schedule cleanup if temp files were created
        # background_tasks.add_task(cleanup, request_id)
        
        logger.info(f"[{request_id}] Success: ATS Score {result.get('ats_score', {}).get('overall_score', 'N/A')}")
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{request_id}] Pipeline error: {str(e)}", exc_info=True)
        raise HTTPException(500, f"Processing failed: {str(e)}")
```

### 5. Health Check Endpoint

```python
@app.get("/")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "AutoApply AI",
        "version": "1.0.0",
        "agents": [
            "ResumeParser", "JDAnalyzer", "GapAnalysis", 
            "ATSScorer", "ResumeRewriter", "CoverLetter"
        ]
    }
```

### 6. Download Endpoints

```python
@app.post("/download/resume/pdf")
async def download_resume_pdf(
    parsed_resume: dict,
    rewritten_resume: dict
):
    """Generate and download optimized resume as PDF."""
    try:
        pdf_bytes = generate_resume_pdf(parsed_resume, rewritten_resume)
        
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=optimized_resume.pdf"
            }
        )
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        raise HTTPException(500, "Failed to generate PDF")


@app.post("/download/resume/word")
async def download_resume_word(
    parsed_resume: dict,
    rewritten_resume: dict
):
    """Generate and download optimized resume as Word document."""
    try:
        docx_bytes = generate_resume_word(parsed_resume, rewritten_resume)
        
        return StreamingResponse(
            io.BytesIO(docx_bytes),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f"attachment; filename=optimized_resume.docx"
            }
        )
    except Exception as e:
        logger.error(f"Word generation failed: {e}")
        raise HTTPException(500, "Failed to generate Word document")


@app.post("/download/cover_letter/pdf")
async def download_cover_letter_pdf(cover_letter: dict):
    """Generate and download cover letter as PDF."""
    try:
        pdf_bytes = generate_cover_letter_pdf(cover_letter.get("content", ""))
        
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=cover_letter.pdf"
            }
        )
    except Exception as e:
        logger.error(f"Cover letter PDF failed: {e}")
        raise HTTPException(500, "Failed to generate cover letter PDF")
```

### 7. Error Response Format

```python
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "status_code": exc.status_code,
            "message": exc.detail,
            "path": str(request.url.path)
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "status_code": 500,
            "message": "Internal server error",
            "path": str(request.url.path)
        }
    )
```

---

## API Response Codes

| Code | Meaning | When Used |
|------|---------|-----------|
| 200 | Success | Normal response |
| 400 | Bad Request | Invalid file format, missing fields |
| 413 | Payload Too Large | File > 5MB |
| 422 | Unprocessable Entity | Invalid JD text, empty content |
| 500 | Internal Error | Pipeline failure, unexpected error |

---

## Data Flow

```
Client (Frontend)
    ↓
POST /process (resume + JD)
    ↓
Validation (file type, size, JD length)
    ↓
Text Extraction (PDF/DOCX → text)
    ↓
Pipeline Execution:
    1. ResumeParser → ParsedResume
    2. JDAnalyzer → ParsedJobDescription
    3. GapAnalysis → GapAnalysis
    4. ATSScorer → ATSScore
    5. ResumeRewriter → RewrittenResume
    6. CoverLetter → CoverLetter
    ↓
JSON Response
    ↓
Client receives full analysis
```

---

## Security Checklist

- [ ] File type validation (not just extension)
- [ ] File size limits enforced
- [ ] JD text length limits
- [ ] No sensitive data in logs
- [ ] Temp files cleaned up
- [ ] CORS properly configured
- [ ] Rate limiting (future)
- [ ] Authentication (future)
