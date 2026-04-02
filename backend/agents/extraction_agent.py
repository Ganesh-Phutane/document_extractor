"""
agents/extraction_agent.py
──────────────────────────
Core agent for extracting structured JSON from document Markdown 
using the Gemini LLM and versioned modular prompts.
"""
from typing import Dict, Any, Optional, Tuple, List
from sqlalchemy.orm import Session

from models.document import Document
from models.extraction import ExtractedData
from models.field_traceability import FieldTraceability
from agents.llm_client import LLMClient
from services.template_service import TemplateService
from services.blob_service import BlobService
from core.logger import get_logger

logger = get_logger(__name__)

class ExtractionAgent:
    def __init__(self, db: Session):
        self.db = db
        self.llm = LLMClient()
        self.template_service = TemplateService(db)
        self.blob_service = BlobService()

    async def extract(self, document_id: str) -> Dict[str, Any]:
        """
        Performs the extraction for a document.
        1. Fetches document and template.
        2. Downloads latest modular prompt.
        3. Downloads document Markdown.
        4. Calls LLM and saves result.
        """
        logger.info(f"ExtractionAgent starting for doc: {document_id}")
        
        doc = self.db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise ValueError(f"Document {document_id} not found")
        
        if not doc.template_id:
            raise ValueError(f"Document {document_id} has no template assigned")

        # 1. Get latest prompt
        modular_prompt = self.template_service.get_latest_prompt(doc.template_id)
        
        # 2. Get document content (Markdown)
        # Assuming processed_path from BlobService leads to the full markdown
        processed_path = self.blob_service.processed_path(document_id)
        markdown_content = self.blob_service.download_text(processed_path)
        
        # 3. Assemble and call LLM
        full_prompt = self.template_service.assemble_full_prompt(modular_prompt, markdown_content)
        
        doc.status = "extracting"
        self.db.commit()

        try:
            raw_response = await self.llm.get_completion(
                prompt=full_prompt,
                system_instruction=modular_prompt.get("system_instruction"),
                json_mode=True
            )
            extracted_json = self.llm.parse_json(raw_response)
            
            # --- SCRUB & MAP TRACEABILITY ---
            clean_json, field_mappings = self._process_traceability(extracted_json)
            
            # 4. Save Extracted Data (CLEAN JSON)
            output_path = self.blob_service.extracted_path(document_id)
            self.blob_service.upload_json(clean_json, output_path)
            
            # 5. Handle versioning: Deactivate older extraction versions for this doc
            self.db.query(ExtractedData).filter(
                ExtractedData.document_id == document_id,
                ExtractedData.is_active_version == True
            ).update({"is_active_version": False}, synchronize_session="fetch")
            
            # 6. Create extraction record
            extraction = ExtractedData(
                document_id=document_id,
                template_id=doc.template_id,
                output_blob_path=output_path,
                model_used=self.llm.model.model_name,
                extraction_version=modular_prompt["version"],
                is_active_version=True
            )
            self.db.add(extraction)
            self.db.commit() # Get extraction ID

            # 7. Save field traceability mappings
            self._save_field_mappings(extraction.id, field_mappings)
            
            # --- SAVE SUMMARY TO DOC STATS (for tabular list view) ---
            # Now dynamic: only take first 5 keys that are not complex objects
            summary = {}
            flat_items = [(k, v) for k, v in clean_json.items() if not isinstance(v, (dict, list))]
            for k, v in flat_items[:5]:
                summary[k] = v
            
            if not doc.stats:
                doc.stats = {}
            doc.stats["extraction_summary"] = summary
            
            doc.status = "extracted"
            self.db.commit()
            
            logger.info(f"Extraction complete for doc: {document_id}")
            return {
                "extraction_id": extraction.id,
                "data": clean_json,
                "version": modular_prompt["version"]
            }

        except Exception as e:
            logger.error(f"ExtractionAgent failed for doc {document_id}: {str(e)}")
            doc.status = "failed"
            self.db.commit()
            raise

    def _process_traceability(self, data: Any, path: str = "") -> Tuple[Any, Dict[str, str]]:
        """
        Recursively scrubs 'source_ref' from JSON and records field paths.
        Returns (clean_data, {field_path: ref_key}).
        """
        mappings = {}
        
        if isinstance(data, dict):
            # Check if this is a value-ref object {"value": ..., "source_ref": ...}
            # Use case-insensitive check for flexibility
            norm_data = {k.lower(): v for k, v in data.items()}
            if "value" in norm_data and ("source_ref" in norm_data or "ref" in norm_data) and len(data) <= 4:
                val = norm_data["value"]
                ref = norm_data.get("source_ref") or norm_data.get("ref")
                if ref: 
                    mappings[path] = str(ref)
                return val, mappings
            
            # Otherwise recurse
            clean_dict = {}
            for k, v in data.items():
                new_path = f"{path}.{k}" if path else k
                clean_v, sub_mappings = self._process_traceability(v, new_path)
                clean_dict[k] = clean_v
                mappings.update(sub_mappings)
            return clean_dict, mappings
            
        elif isinstance(data, list):
            clean_list = []
            for i, item in enumerate(data):
                new_path = f"{path}[{i}]"
                clean_item, sub_mappings = self._process_traceability(item, new_path)
                clean_list.append(clean_item)
                mappings.update(sub_mappings)
            return clean_list, mappings
            
        return data, mappings

    def _save_field_mappings(self, extraction_id: str, mappings: Dict[str, str]):
        """Saves traceability mappings to DB."""
        db_mappings = [
            FieldTraceability(
                extraction_id=extraction_id,
                field_path=path,
                ref_key=ref
            ) for path, ref in mappings.items()
        ]
        self.db.add_all(db_mappings)
        self.db.commit()
