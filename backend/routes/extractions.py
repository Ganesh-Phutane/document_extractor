"""
routes/extractions.py
──────────────────────
Combined endpoints for Azure DI extraction and iterative Gemini extraction.
"""
from typing import Annotated, List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.dependencies import get_db, get_current_user
from core.logger import get_logger
from models.user import User
from models.document import Document
from models.extraction import ExtractedData
from models.field_traceability import FieldTraceability
from models.source_mapping import SourceMapping
from services import extraction_service
from services.blob_service import BlobService
from agents.reextraction_agent import ReExtractionAgent
import re

logger = get_logger(__name__)

router = APIRouter(tags=["Extractions"])

# ── Azure DI (Markdown Generation) ───────────────────────
@router.post("/trigger/{document_id}", status_code=status.HTTP_202_ACCEPTED)
def trigger_azure_extraction(
    document_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Triggers Azure Document Intelligence for a specific document.
    """
    try:
        result = extraction_service.process_document(db, document_id)
        return result
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Azure DI failed: {str(e)}")

from pydantic import BaseModel

class ExtractionRequest(BaseModel):
    user_goal: Optional[str] = None
    template_id: Optional[str] = None

# ── Gemini (Iterative Data Extraction) ───────────────────
@router.post("/{document_id}/run", status_code=status.HTTP_200_OK)
async def run_gemini_extraction(
    document_id: str,
    request: ExtractionRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Triggers the iterative Gemini extraction pipeline with an optional user goal.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    # Ensure document has been processed by Azure DI first
    if doc.status == "uploaded" or doc.status == "di_processing":
        raise HTTPException(
            status_code=400,
            detail=f"Document is in state '{doc.status}'. Please wait for Azure DI processing to complete."
        )

    # Assign template if provided in the request, otherwise look for default "financial_document"
    if request.template_id:
        doc.template_id = request.template_id
        db.commit()
    
    if not doc.template_id:
        # Fallback to default financial template
        from models.template import PromptTemplate
        default_template = db.query(PromptTemplate).filter(PromptTemplate.document_type == "financial_document").first()
        if default_template:
            doc.template_id = default_template.id
            db.commit()
            logger.info(f"Auto-assigned default template '{default_template.name}' to document {document_id}")
        else:
            raise HTTPException(
                status_code=400,
                detail="No template assigned and no default 'financial_document' template found."
            )

    agent = ReExtractionAgent(db)
    
    # Use template field mapping as default goal if none provided
    user_goal = request.user_goal
    if not user_goal:
        from models.template import PromptTemplate
        template = db.query(PromptTemplate).filter(PromptTemplate.id == doc.template_id).first()
        if template and template.field_mapping:
            column_names = ", ".join([c.get("label", c.get("id")) for c in template.field_mapping])
            user_goal = f"""Perform a comprehensive extraction of all financial data, tables, and key metrics found in the document. 
            Your primary objective is to extract ALL relevant financial information, especially tabular data and line items. 
            Additionally, you MUST specifically identify and extract the following fields as top-level JSON keys: {column_names}. 
            IMPORTANT: If any of these fields are found within a table (e.g., Total Revenue in a Financial Summary table), you MUST still extract that specific value into the corresponding top-level key (e.g., 'Total Amount'). 
            Map them from equivalent document labels (e.g., 'Vendor' or 'Issuer' should map to 'Vendor Name'). 
            If a listed field is truly not found anywhere in the document, use null."""
    
    try:
        result = await agent.run_pipeline(document_id, user_goal=user_goal)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/{document_id}/template", status_code=status.HTTP_200_OK)
def update_document_template(
    document_id: str,
    template_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Assigns a template to a document before extraction.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc.template_id = template_id
    db.commit()
    return {"message": "Template assigned successfully"}

@router.get("/{document_id}/result", status_code=status.HTTP_200_OK)
def get_latest_extraction_result(
    document_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Retrieves the latest active extraction result for a document.
    """
    extraction = db.query(ExtractedData).filter(
        ExtractedData.document_id == document_id,
        ExtractedData.is_active_version == True
    ).first()
    
    if not extraction:
        raise HTTPException(status_code=404, detail="No extraction found for this document")
        
    blob_service = BlobService()
    data = blob_service.download_json(extraction.output_blob_path)
    
    # Generate temporary SAS URL for the source document
    try:
        document_url = blob_service.generate_sas_url(extraction.document.blob_path)
    except Exception as e:
        logger.warning(f"Failed to generate SAS URL for {extraction.document_id}: {e}")
        document_url = None

    # Infer doc_type if missing
    doc_type = extraction.document.doc_type
    if not doc_type and extraction.document.filename:
        name_lower = extraction.document.filename.lower()
        if name_lower.endswith('.pdf'): doc_type = 'pdf'
        elif any(name_lower.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.webp']): doc_type = 'image'

    return {
        "extraction_id": extraction.id,
        "document_url": document_url,
        "confidence": extraction.confidence_score,
        "version": extraction.extraction_version,
        "data": data,
        "status": extraction.document.status,
        "filename": extraction.document.filename,
        "doc_type": doc_type
    }

@router.get("/{extraction_id}/trace", status_code=status.HTTP_200_OK)
def get_field_traceability(
    extraction_id: str,
    field_path: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Resolves a field path to its physical source coordinates.
    """
    # 1. Direct Lookup
    ft = db.query(FieldTraceability).filter(
        FieldTraceability.extraction_id == extraction_id,
        FieldTraceability.field_path == field_path
    ).first()
    
    # 2. Heuristic Lookup (Fuzzy match case and underscores/spaces)
    if not ft:
        # Fetch all mappings for this extraction to find a close match
        # (This is more efficient than database-level fuzzy matches in small-scale)
        all_fts = db.query(FieldTraceability).filter(FieldTraceability.extraction_id == extraction_id).all()
        
        def normalize_path(p):
            return p.lower().replace("_", " ").replace("-", " ")
        
        target = normalize_path(field_path)
        for candidate in all_fts:
            if normalize_path(candidate.field_path) == target:
                ft = candidate
                break
    
    if not ft:
        # 3. Content-Based Fallback (Search Markdown for the value)
        try:
            extraction = db.query(ExtractedData).filter(ExtractedData.id == extraction_id).first()
            if extraction:
                blob_service = BlobService()
                # Get clean data
                data = blob_service.download_json(extraction.output_blob_path)
                
                # Resolve value from path
                segments = re.split(r'[.\[\]]+', field_path)
                segments = [s for s in segments if s]
                val = data
                for seg in segments:
                    if isinstance(val, list):
                        try: val = val[int(seg)]
                        except: val = None; break
                    elif isinstance(val, dict):
                        val = val.get(seg)
                    else:
                        val = None; break
                
                if val and not isinstance(val, (dict, list)):
                    # Get markdown
                    doc = extraction.document
                    markdown_content = blob_service.download_text(blob_service.processed_path(doc.id))
                    
                    # Robust Content-Based Fallback
                    clean_val = str(val).strip()
                    if clean_val:
                        # Helper to find tag in vicinity
                        def find_tag_in_text(text):
                            match = re.search(r"\[\[(.*?)\]\]", text)
                            return match.group(1) if match else None

                        # 1. FAST EXACT MATCH
                        idx = markdown_content.find(clean_val)
                        tag_found = None
                        if idx != -1:
                            # Check after
                            tag_found = find_tag_in_text(markdown_content[idx + len(clean_val) : idx + len(clean_val) + 400])
                            # Check before if not found after
                            if not tag_found:
                                tag_found = find_tag_in_text(markdown_content[max(0, idx - 400) : idx])
                            
                            if tag_found: logger.info(f"Fast-match found tag: {tag_found}")

                        # 2. NUMERIC ROBUST MATCH
                        if not tag_found and clean_val.replace('.', '', 1).isdigit():
                            num_digits = "".join([d for d in clean_val if d.isdigit()])
                            if num_digits:
                                num_pattern = r'[^\d]*'.join(list(num_digits))
                                num_match = re.search(num_pattern, markdown_content)
                                if num_match:
                                    # Check after
                                    tag_found = find_tag_in_text(markdown_content[num_match.end() : num_match.end() + 400])
                                    # Check before
                                    if not tag_found:
                                        tag_found = find_tag_in_text(markdown_content[max(0, num_match.start() - 400) : num_match.start()])
                                    
                                    if tag_found: logger.info(f"Numeric-match found tag: {tag_found}")

                        # 3. FUZZY WORDS MATCH
                        if not tag_found:
                            words = re.findall(r'[a-zA-Z0-9]+', clean_val)
                            if words:
                                pattern_str = r'[^a-zA-Z0-9]+'.join([re.escape(w) for w in words])
                                for match in re.finditer(pattern_str, markdown_content, re.IGNORECASE):
                                    # Check after
                                    tag_found = find_tag_in_text(markdown_content[match.end() : match.end() + 400])
                                    # Check before
                                    if not tag_found:
                                        tag_found = find_tag_in_text(markdown_content[max(0, match.start() - 400) : match.start()])
                                    
                                    if tag_found:
                                        logger.info(f"Fuzzy-match found tag: {tag_found}")
                                        break
                        
                        if tag_found:
                            # Auto-create entry
                            ft = FieldTraceability(
                                extraction_id=extraction_id,
                                field_path=field_path,
                                ref_key=tag_found
                            )
                            db.add(ft)
                            db.commit()
                            logger.info(f"RESOLVED fallback for '{field_path}' -> {tag_found}")
                        else:
                            logger.info(f"Found text but no [[ref]] tag within vicinity for '{clean_val}'")
        except Exception as e:
            logger.error(f"Fallback Traceability CRASHED: {e}", exc_info=True)

    # Content to help frontend scroll-to-match if no coordinate is found
    matched_text = None
    if not ft:
        try:
            extraction = db.query(ExtractedData).filter(ExtractedData.id == extraction_id).first()
            if extraction:
                blob_service = BlobService()
                data = blob_service.download_json(extraction.output_blob_path)
                segments = re.split(r'[.\[\]]+', field_path)
                segments = [s for s in segments if s]
                val = data
                for seg in segments:
                    if isinstance(val, list):
                        try: val = val[int(seg)]
                        except: val = None; break
                    elif isinstance(val, dict): val = val.get(seg)
                    else: val = None; break
                
                if val and not isinstance(val, (dict, list)):
                    matched_text = str(val).strip()
        except: pass

    if not ft:
        return {
            "file_type": "unknown",
            "page": 1,
            "bbox": None,
            "row": None,
            "column": None,
            "xpath": None,
            "trace_found": True if matched_text else False,
            "matched_text": matched_text,
            "tracking_type": "text" if matched_text else None
        }
        
    extraction = db.query(ExtractedData).filter(ExtractedData.id == extraction_id).first()
    sm = db.query(SourceMapping).filter(
        SourceMapping.document_id == extraction.document_id,
        SourceMapping.ref_key == ft.ref_key
    ).first()
    
    if not sm:
        # Fallback to text match if mapping fails
        return { "trace_found": True if matched_text else False, "matched_text": matched_text, "tracking_type": "text" }
        
    return {
        "file_type": sm.file_type,
        "page": sm.page_number,
        "bbox": sm.bbox,
        "row": sm.row_index,
        "column": sm.col_index,
        "xpath": sm.xpath,
        "trace_found": True,
        "matched_text": matched_text,
        "tracking_type": "coordinate"
    }
