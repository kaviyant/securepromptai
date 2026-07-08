from fastapi import APIRouter, Depends, Query, HTTPException, status
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.database.connection import get_database
from app.api.dependencies import get_current_admin
from app.services.report_service import ReportService
from typing import Dict, Any

router = APIRouter(tags=["Reports & Compliance"])

@router.post("/api/report")
async def generate_audit_report(
    format: str = Query("json", pattern="^(json|pdf)$", description="Report file output format"),
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_admin: Dict[str, Any] = Depends(get_current_admin)
):
    """
    Generates a security compliance audit report of warning/blocked prompts logs.
    Supports 'json' payload return or 'pdf' file attachment streaming.
    Restricted to Admins.
    """
    if format == "json":
        return await ReportService.generate_json_report(db)
        
    elif format == "pdf":
        try:
            requestor_username = current_admin.get("username", "Administrator")
            # Generate the PDF file inside in-memory BytesIO stream
            pdf_buffer = await ReportService.generate_pdf_report(db, requestor_username)
            
            # Reset stream pointer
            pdf_buffer.seek(0)
            
            # Stream the PDF file back to the browser
            filename = f"secureprompt_compliance_report_{int(pdf_buffer.getbuffer().nbytes)}.pdf"
            return StreamingResponse(
                pdf_buffer,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f"attachment; filename={filename}"
                }
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error compiling compliance PDF report: {str(e)}"
            )
            
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Unsupported report format request."
    )
