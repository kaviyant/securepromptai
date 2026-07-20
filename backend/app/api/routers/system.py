from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.database.connection import get_database
from app.api.dependencies import get_current_admin, get_current_employee
from app.config.settings import settings
from app.services.ocr_service import OcrService
from app.services.file_service import FileService
from engine.firewall import PromptFirewall
import time
import json
from typing import Dict, Any

router = APIRouter(tags=["System Services"])
ocr_service = OcrService()
file_service = FileService()
firewall = PromptFirewall()

@router.get("/api/health", response_model=Dict[str, Any])
async def check_health(
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Database ping diagnostic health status endpoint.
    """
    start_time = time.time()
    db_status = "unhealthy"
    latency_ms = 999.9
    
    try:
        await db.command("ping")
        db_status = "healthy"
        latency_ms = round((time.time() - start_time) * 1000, 2)
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "healthy",
        "timestamp": time.time(),
        "database": {
            "status": db_status,
            "latency_ms": latency_ms
        },
        "version": "1.0.0"
    }

@router.post("/api/upload", response_model=Dict[str, Any])
async def upload_custom_policy(
    file: UploadFile = File(...),
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_admin: Dict[str, Any] = Depends(get_current_admin)
):
    """
    Uploads policy definitions in JSON format to update database rules.
    Restricted to Admins.
    """
    if not file.filename.endswith(".json"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only JSON policies file uploads are supported."
        )

    try:
        contents = await file.read()
        policies_list = json.loads(contents.decode("utf-8"))

        if not isinstance(policies_list, list):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="JSON root must be a list of policy objects."
            )

        inserted_count = 0
        updated_count = 0

        for policy in policies_list:
            name = policy.get("name")
            if not name:
                continue
                
            doc = {
                "name": name,
                "description": policy.get("description", ""),
                "sensitivity": int(policy.get("sensitivity", 50)),
                "is_active": bool(policy.get("is_active", True))
            }
            
            result = await db.policies.update_one(
                {"name": name},
                {"$set": doc},
                upsert=True
            )
            
            if result.matched_count > 0:
                updated_count += 1
            else:
                inserted_count += 1

        return {
            "success": True,
            "filename": file.filename,
            "details": {
                "inserted": inserted_count,
                "updated": updated_count
            }
        }
        
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File contains invalid JSON markup."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process policy file upload: {str(e)}"
        )

@router.post("/api/upload/ocr", response_model=Dict[str, Any])
async def scan_image_ocr(
    file: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(get_current_employee)
):
    """
    Uploads an image file, extracts text via OCR, and runs prompt firewall security scan on it.
    Gated by Employee role access.
    """
    ext = file.filename.split(".")[-1].lower()
    if ext not in ["png", "jpg", "jpeg", "bmp", "tiff"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported image format. Upload PNG, JPG, or JPEG."
        )

    try:
        contents = await file.read()
        extracted_text = ocr_service.extract_text(contents)
        
        if not extracted_text.strip():
            return {
                "filename": file.filename,
                "scanned": True,
                "extracted_text": "",
                "risk_score": 0,
                "risk_level": "LOW",
                "action": "ALLOW",
                "explanation": "Compliant: Image contains no readable text."
            }

        # Analyze extracted text via firewall
        firewall_res = firewall.scan_and_decide(
            prompt_text=extracted_text,
            department=current_user.get("department", "General Operations")
        )

        return {
            "filename": file.filename,
            "scanned": True,
            "extracted_text": extracted_text,
            "risk_score": firewall_res["risk_score"],
            "risk_level": firewall_res["risk_level"],
            "action": firewall_res["action"],
            "explanation": firewall_res["explanation"],
            "details": {
                "category": firewall_res["category"],
                "source_code": firewall_res["source_code"]
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OCR processing failed: {str(e)}"
        )

@router.post("/api/upload/file", response_model=Dict[str, Any])
async def scan_uploaded_document(
    file: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(get_current_employee)
):
    """
    Uploads a business document (PDF, DOCX, CSV, Excel, TXT) and runs prompt firewall scans on it.
    Gated by Employee role access.
    """
    try:
        contents = await file.read()
        department = current_user.get("department", "General Operations")
        
        # Scan file using FileService
        result = await file_service.scan_file(
            file_bytes=contents,
            filename=file.filename,
            department=department
        )
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
            
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File scanning failed: {str(e)}"
        )

@router.post("/api/documents/index", response_model=Dict[str, Any])
async def index_document(
    doc_id: str = None,
    file: UploadFile = File(...),
    current_admin: Dict[str, Any] = Depends(get_current_admin)
):
    """
    Uploads a business document and indexes it in the similarity database.
    Subsequent user prompts similar to this document will be blocked by the PromptFirewall.
    Restricted to Admins.
    """
    try:
        contents = await file.read()
        target_doc_id = doc_id or file.filename
        
        result = await file_service.index_file(
            file_bytes=contents,
            filename=file.filename,
            doc_id=target_doc_id
        )
        
        if not result.get("indexed"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to index file.")
            )
            
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to index document: {str(e)}"
        )
