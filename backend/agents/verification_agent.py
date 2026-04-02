"""
agents/verification_agent.py
────────────────────────────
Agent for cross-verifying extracted JSON data against the source Markdown.
Calculates confidence and logs discrepancies.
"""
import time
import json
from typing import Dict, Any, List, Tuple
from sqlalchemy.orm import Session

from models.extraction import ExtractedData
from models.verification import VerificationLog
from models.document import Document
from services.blob_service import BlobService
from core.logger import get_logger

logger = get_logger(__name__)

class VerificationAgent:
    def __init__(self, db: Session):
        self.db = db
        self.blob_service = BlobService()

    def verify(self, extraction_id: str) -> Dict[str, Any]:
        """
        Verifies the results of an extraction.
        1. Compares JSON fields with source Markdown text.
        2. Identifies missing or 'hallucinated' values.
        3. Calculates confidence score.
        """
        logger.info(f"VerificationAgent starting for extraction: {extraction_id}")
        
        extraction = self.db.query(ExtractedData).filter(ExtractedData.id == extraction_id).first()
        if not extraction:
            raise ValueError(f"Extraction {extraction_id} not found")
        
        doc = extraction.document
        
        # 1. Download Markdown and Extracted JSON
        markdown_text = self.blob_service.download_text(self.blob_service.processed_path(doc.id)).lower()
        extracted_data = self.blob_service.download_json(extraction.output_blob_path)
        
        issues = []
        total_fields = 0
        passed_fields = 0
        
        # 2. Recursive check function
        def check_value(val) -> Tuple[int, int]:
            p, t = 0, 0
            if isinstance(val, dict):
                for v in val.values():
                    cp, ct = check_value(v)
                    p += cp
                    t += ct
            elif isinstance(val, list):
                for item in val:
                    cp, ct = check_value(item)
                    p += cp
                    t += ct
            elif val is not None and str(val).strip() != "":
                t += 1
                if str(val).lower() in markdown_text:
                    p += 1
                else:
                    # Log issue if not found
                    issues.append({
                        "field_name": "generic", # Will be context-aware in refined logs
                        "issue_type": "mismatch",
                        "severity": "medium",
                        "message": f"Value '{val}' not found in source text."
                    })
            return p, t

        passed_fields, total_fields = check_value(extracted_data)

        # 3. Calculate Confidence
        confidence = (passed_fields / total_fields) if total_fields > 0 else 1.0
        status = "passed" if confidence >= 0.9 else "failed"
        
        # 4. Save detailed report to Blob
        report = {
            "extraction_id": extraction_id,
            "document_id": doc.id,
            "confidence": confidence,
            "total_fields": total_fields,
            "passed_fields": passed_fields,
            "issues": issues,
            "verified_at": time.time()
        }
        report_path = self.blob_service.log_path(doc.id, int(time.time()))
        self.blob_service.upload_json(report, report_path)
        
        # 5. Save Summary to DB
        v_log = VerificationLog(
            extracted_data_id=extraction_id,
            document_id=doc.id,
            overall_confidence=confidence,
            report_blob_path=report_path,
            status=status,
            field_issues_summary=[
                {"field_name": i["field_name"], "issue_type": i["issue_type"]} 
                for i in issues[:5] # Store top 5 as summary
            ]
        )
        self.db.add(v_log)
        
        # Update extraction record with confidence
        extraction.confidence_score = confidence
        extraction.is_validated = (status == "passed")
        
        self.db.commit()
        
        logger.info(f"Verification complete for doc {doc.id}. Confidence: {confidence}")
        return {
            "log_id": v_log.id,
            "confidence": confidence,
            "status": status,
            "issues": issues
        }
