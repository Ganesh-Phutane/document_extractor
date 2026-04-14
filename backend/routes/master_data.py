"""
routes/master_data.py
──────────────────────
API endpoints for the Master Data Processing Engine.

This router is INDEPENDENT of the existing extraction pipeline.
It adds a new /master prefix and does not modify any existing routes.

Endpoints:
  POST  /master/{document_id}/process  → runs md_converter + master_data_service
  GET   /master/{document_id}/latest   → retrieves saved result from blob
  PATCH /master/{document_id}/approve  → marks result as approved (sets flag in JSON)
"""
from typing import Annotated, Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from core.dependencies import get_db, get_current_user
from core.logger import get_logger
from models.user import User
from models.document import Document
from services.blob_service import BlobService
from services import md_converter, master_data_service
from schemas.master_data import MasterDataResolveRequest
from models.master_data import MasterData, MasterDataRecord
from azure.core.exceptions import ResourceNotFoundError
from datetime import datetime, timezone


logger = get_logger(__name__)

router = APIRouter(tags=["Master Data"])


# ── POST /master/{document_id}/process ───────────────────────
@router.post("/{document_id}/process", status_code=status.HTTP_200_OK)
async def process_master_data(
    document_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    extra_columns: str = Query(
        "",
        description=(
            "Comma-separated list of additional financial columns to extract "
            "(e.g. 'Operating Income, EPS'). If provided, Gemini will specifically "
            "look for these fields. Default: empty string."
        ),
    ),
):
    """
    Triggers the full master data pipeline for a document:
      1. Converts Gemini JSON → compact Markdown (saved to master/{id}.md)
      2. Extracts, validates, verifies, and scores the 4 KPI fields
      3. Saves result to master/{id}_result.json in blob
    
    Requires the document to have been extracted first (status: extracted or verified).
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    # Guard: must have gone through Gemini extraction
    allowed_statuses = {"extracted", "verified", "manual_review_required", "reextracting"}
    if doc.status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Document is in state '{doc.status}'. "
                f"Master data processing requires a completed extraction. "
                f"Allowed states: {sorted(allowed_statuses)}"
            )
        )

    bs = BlobService()

    try:
        # Step 1: Convert Gemini JSON → compact Markdown
        logger.info(f"[MasterData Route] Starting MD conversion for doc: {document_id}")
        markdown_content = md_converter.convert(document_id, blob_service=bs)

        # Step 2: Run full master data pipeline
        logger.info(f"[MasterData Route] Starting master data processing for doc: {document_id}")
        result = await master_data_service.process(
            document_id,
            markdown_content,
            db=db,
            extra_columns=extra_columns,
        )

        return result

    except ResourceNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=(
                "Extracted JSON not found in blob storage. "
                "Please ensure the Gemini extraction step completed successfully."
            )
        )
    except Exception as e:
        logger.error(f"[MasterData Route] Pipeline failed for {document_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Master data processing failed: {str(e)}")


# ── GET /master/{document_id}/latest ─────────────────────────
@router.get("/{document_id}/latest", status_code=status.HTTP_200_OK)
def get_master_data(
    document_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Retrieves the latest master data result.
    Tries DB first to get the path, then downloads from blob.
    """
    from models.master_data import MasterData
    master_rec = db.query(MasterData).filter(MasterData.document_id == document_id).first()
    
    bs = BlobService()
    result_path = master_rec.blob_path if master_rec else BlobService.master_json_path(document_id)

    try:
        result = bs.download_json(result_path)
        return result
    except ResourceNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Master data not yet processed for this document. Run POST /process first."
        )
    except Exception as e:
        logger.error(f"[MasterData Route] Failed to fetch result for {document_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── PATCH /master/{document_id}/approve ──────────────────────
@router.patch("/{document_id}/approve", status_code=status.HTTP_200_OK)
def approve_master_data(
    document_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Marks the current master data result as approved in both DB and Blob.
    """
    from models.master_data import MasterData
    master_rec = db.query(MasterData).filter(MasterData.document_id == document_id).first()
    if not master_rec:
         # Check if it exists in blob before failing
         bs_check = BlobService()
         if not bs_check.exists(BlobService.master_json_path(document_id)):
             raise HTTPException(status_code=404, detail="No master data result found. Run POST /process first.")

    bs = BlobService()
    result_path = master_rec.blob_path if master_rec else BlobService.master_json_path(document_id)

    try:
        result = bs.download_json(result_path)
    except ResourceNotFoundError:
        raise HTTPException(status_code=404, detail="No master data result found.")

    now_ts = datetime.now(timezone.utc)
    
    result["is_approved"] = True
    result["approved_at"] = now_ts.isoformat()
    result["approved_by"] = current_user.email

    # Sync to Blob
    bs.upload_json(result, result_path)

    # Sync to DB
    if master_rec:
        master_rec.is_approved = True
        master_rec.updated_at = now_ts
        db.commit()

    logger.info(f"[MasterData Route] Record approved for doc {document_id} by {current_user.email}")
    return {
        "message": "Master data record approved successfully.",
        "document_id": document_id,
        "approved_at": result["approved_at"],
        "approved_by": result["approved_by"],
    }


@router.get("/data", status_code=status.HTTP_200_OK)
async def get_master_data_only(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Fetches all master data records but returns ONLY the financial data columns.
    Excluded: id, document_id, created_at, filename, etc.
    Includes: Flattened extra_fields.
    """
    try:
        # Join with Document to get the filename
        records = db.query(MasterDataRecord, Document.filename).join(
            Document, MasterDataRecord.document_id == Document.id
        ).all()
        
        result = []
        for rec, filename in records:
            # 1. Start with fixed columns + metadata for viewer
            row = {
                "document_id": rec.document_id,
                "filename": filename,
                "company_name": rec.company_name,
                "period": rec.period,
                "frequency": rec.frequency,
                "gross_sales": rec.gross_sales,
                "ebita": rec.ebita,
                "net_revenue": rec.net_revenue,
                "gross_profit": rec.gross_profit,
                "total_debt": rec.total_debt,
                "extraction_id": getattr(rec.master_data, "extraction_id", None),
            }
            
            # 2. Flatten extra fields if any
            if rec.extra_fields and isinstance(rec.extra_fields, dict):
                row.update(rec.extra_fields)
            
            result.append(row)
            
        return result

    except Exception as e:
        logger.error(f"[MasterData Route] Error fetching data-only records: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── GET /master/pending-review ───────────────────────────────
@router.get("/pending-review", status_code=status.HTTP_200_OK)
async def get_pending_review(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Fetches all master data records that failed validation or have conflicts.
    """
    records = db.query(MasterData).filter(
        MasterData.validation_status.in_(["validation_failed", "conflict_detected"])
    ).all()
    
    # We want to return the full payload for the UI to compare
    results = []
    bs = BlobService()
    for rec in records:
        try:
            data = bs.download_json(rec.blob_path)
            # Add some metadata for the UI
            data["validation_status"] = rec.validation_status
            data["validation_issues"] = rec.validation_issues
            results.append(data)
        except Exception:
            continue
    return results


# ── POST /master/{document_id}/resolve ───────────────────────
@router.post("/{document_id}/resolve", status_code=status.HTTP_200_OK)
async def resolve_master_data(
    document_id: str,
    payload: MasterDataResolveRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Resolves a validation/conflict state by either accepting, rejecting, or providing edited data.
    If 'accept' or 'edit', it proceeds to create MasterDataRecord entries.
    """
    master_rec = db.query(MasterData).filter(MasterData.document_id == document_id).first()
    if not master_rec:
        raise HTTPException(status_code=404, detail="Master data record not found.")

    bs = BlobService()
    
    if payload.action == "reject":
        now_ts = datetime.now(timezone.utc)
        
        # 1. Update Database Status
        master_rec.validation_status = "validation_passed" 
        master_rec.validation_issues = []
        master_rec.is_approved = False 
        master_rec.updated_at = now_ts
        
        # 2. Update Blob (JSON) Status so the UI hides the banner
        try:
            data = bs.download_json(master_rec.blob_path)
            data["validation_status"] = "validation_passed"
            data["validation_issues"] = []
            bs.upload_json(data, master_rec.blob_path)
        except Exception as e:
            logger.error(f"[MasterData Route] Failed to sync rejection to blob: {e}")
            # We still commit DB changes since the resolve succeeded
            
        db.commit()
        logger.info(f"[MasterData Route] Record {document_id} rejected (manually marked resolved) by {current_user.email}")
        return {"message": "Record rejected. Validation flags cleared in repository."}

    # If 'accept' or 'edit', we need the final data to persist
    final_data = None
    if payload.action == "accept":
        final_data = bs.download_json(master_rec.blob_path)
    elif payload.action == "edit":
        if not payload.resolved_data:
            raise HTTPException(status_code=400, detail="Missing resolved_data for 'edit' action.")
        final_data = payload.resolved_data
    
    if not final_data:
         raise HTTPException(status_code=400, detail="Could not determine final data for resolution.")

    # 1. Update status and clear issues in both DB and JSON
    master_rec.validation_status = "validation_passed"
    master_rec.validation_issues = []
    master_rec.is_approved = True # Auto-approve upon resolution
    
    # CRITICAL: Update the JSON body so save_to_db doesn't see a conflict!
    final_data["validation_status"] = "validation_passed"
    final_data["validation_issues"] = []
    
    # 2. Sync to Blob (Always update blob to clear status flags for the UI)
    bs.upload_json(final_data, master_rec.blob_path)

    # 3. Trigger Persistence to Master Tables
    try:
        from services.master_data_service import save_to_db, _load_prompt_config
        prompt_config = _load_prompt_config(bs)
        
        save_to_db(
            document_id=document_id,
            company_name=final_data.get("company_name"),
            std_periods_list=final_data.get("periods", []),
            final_financials=final_data.get("financials", {}),
            clean_extra_fields=final_data.get("extra_fields", {}),
            confidence=final_data.get("confidence_score", 0),
            result_path=master_rec.blob_path,
            db=db,
            prompt_config=prompt_config,
            output=final_data
        )
        return {"message": f"Record resolved and saved successfully via {payload.action}."}
    except Exception as e:
        logger.error(f"[MasterData Route] Resolution failed for {document_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Resolution failed: {str(e)}")
