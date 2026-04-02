"""
services/template_service.py
───────────────────────────
Service for managing document extraction templates, field mappings, 
and modular prompt versioning.
"""
import uuid
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session
from models.template import PromptTemplate
from models.prompt_version import PromptVersion
from services.blob_service import BlobService
from core.logger import get_logger

logger = get_logger(__name__)

GLOBAL_FINANCIAL_RULES = """
STRICT EXTRACTION GUIDELINES:
1. CORE FOCUS: Extract quantitative financial metrics and data rows ONLY.
2. EXCLUSION CRITERIA (NOISE):
   - IGNORE Index pages, Table of Contents, and navigation sections.
   - IGNORE section lists (tables that only link sections to page numbers).
3. DATA FORMAT (WRAPPED ARRAY):
   - You MUST return a JSON OBJECT.
   - All financial tables must be contained within descriptive keys (e.g., "financial_metrics", "balance_sheet").
   - Values for these keys MUST be an ARRAY of OBJECTS.
   - Each object in the array MUST represent exactly one ROW.
   - Column headers MUST be the keys in the objects.
   - EXAMPLE OF CORRECT FORMAT:
     {
       "financial_metrics": [
         {"Line Item": "Net Sales", "Actual 2023": 86015, "Actual 2024": 100054},
         {"Line Item": "Gross Profit", "Actual 2023": 48692, "Actual 2024": 57306}
       ]
     }
4. PRECISION: If a header is "Index", skip it. If it's "Financial Overview", extract the table under a key named "financial_overview".
5. SOURCE TRACEABILITY (MANDATORY ADD-ON):
   - You will see hidden reference tags like [[ref_N]] or [[r1_c1]] in the markdown.
   - For every extracted field, you MUST return a JSON object containing:
     "value": (the actual extracted data),
     "source_ref": (the exact text inside the [[...]] tag found closest to the source content).
   - EXAMPLE: 
     "Net Sales": { "value": 86015, "source_ref": "ref_42" }
   - If no tag is found for a field, use null for source_ref.
   - IMPORTANT: Do NOT let this rule break the core Table/Array structure defined in Rule 3.
"""

class TemplateService:
    def __init__(self, db: Session):
        self.db = db
        self.blob_service = BlobService()

    def get_template_by_type(self, doc_type: str) -> Optional[PromptTemplate]:
        """Fetches the template for a document type."""
        return self.db.query(PromptTemplate).filter(PromptTemplate.document_type == doc_type).first()

    def create_template(self, name: str, doc_type: str, field_mapping: Optional[List[Dict[str, Any]]] = None) -> PromptTemplate:
        """Initializes a new template."""
        template = PromptTemplate(
            name=name,
            document_type=doc_type,
            field_mapping=field_mapping or []
        )
        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)
        
        # Create initial V1 prompt
        self.create_prompt_version(template.id, "initial_manual")
        return template

    async def refine_user_goal(self, user_goal: str) -> str:
        """
        Uses Gemini to transform a simple user request into a detailed
        system instruction and target JSON schema.
        """
        prompt = f"""
        TRANSFORM THE FOLLOWING USER EXTRACTION GOAL INTO A DETAILED SYSTEM PROMPT FOR AN LLM.
        
        USER GOAL: "{user_goal}"
        
        YOUR TASK:
        Create a comprehensive instruction set that:
        1. Defines the EXACT JSON structure to be returned.
        2. Lists specific fields to look for based on the goal. EMPHASIZE that these fields are MANDATORY in the output.
        3. Incorporates the following STRICT RULES every time:
           {GLOBAL_FINANCIAL_RULES}
        4. Adds guidelines for handling missing data: Explicitly state that if a requested field is not found, it MUST be included in the JSON with a value of `null`.
        5. Ensures the output is PURE JSON only.
        
        OUTPUT FORMAT:
        Return ONLY the text of the generated system prompt. Do not add any preamble.
        The prompt should start with "YOUR ROLE: You are an expert data extraction agent..."
        """
        
        from agents.llm_client import LLMClient
        client = LLMClient()
        # json_mode=False because we want plain text instructions, not JSON
        refined_prompt = await client.get_completion(prompt, json_mode=False)
        return refined_prompt

    async def create_prompt_version_from_goal(self, template_id: str, user_goal: str):
        """
        Refines a user goal and saves it as a prompt version.
        On first run (v0), saves as v1. Otherwise increments the existing version.
        """
        refined_content = await self.refine_user_goal(user_goal)
        
        template = self.db.query(PromptTemplate).filter(PromptTemplate.id == template_id).first()
        if not template:
            raise ValueError("Template not found")

        # Determine version number (first run is v1)
        current_v_str = template.current_prompt_version or "v0"
        try:
            current_v_num = int(current_v_str.lstrip("v"))
        except (ValueError, AttributeError):
            current_v_num = 0
        next_v_num = current_v_num + 1
        next_v = f"v{next_v_num}"

        blob_path = self.blob_service.prompt_path(template.document_type, next_v)
        
        prompt_data = {
            "version": next_v,
            "user_goal": user_goal,
            "system_instruction": refined_content,
            "previous_corrections": "",
            "iterations": []
        }
        
        self.blob_service.upload_json(prompt_data, blob_path)
        
        # Create DB record for version history
        pv = PromptVersion(
            template_id=template_id,
            version_number=next_v,
            prompt_blob_path=blob_path,
            trigger_reason="goal_refinement",
            correction_blob_path=None
        )
        self.db.add(pv)

        # ✅ Critical: update BOTH fields on template
        template.current_prompt_version = next_v
        template.optimized_prompt_blob_path = blob_path
        self.db.commit()
        
        logger.info(f"Created prompt {next_v} from user goal for template {template_id}")
        return prompt_data

    def create_prompt_version(self, template_id: str, trigger: str, corrections: Optional[str] = None) -> PromptVersion:
        """
        Generates and saves a new modular prompt version.
        Saves the modular structure to Blob and creates a DB record.
        """
        template = self.db.query(PromptTemplate).filter(PromptTemplate.id == template_id).first()
        if not template:
            raise ValueError("Template not found")

        # Increment version
        current_v = template.current_prompt_version # e.g. "v1"
        next_v_num = int(current_v[1:]) + 1
        next_v = f"v{next_v_num}"

        # Construct modular prompt components
        prompt_modular = {
            "version": next_v,
            "template_name": template.name,
            "document_type": template.document_type,
            "system_instruction": (
                "You are a specialized document extraction engine. "
                f"Your goal is to extract structured data from Markdown for an '{template.document_type}' file."
            ),
            "previous_corrections": corrections or ""
        }

        # Save to Blob
        blob_path = self.blob_service.prompt_path(template.document_type, next_v)
        self.blob_service.upload_json(prompt_modular, blob_path)

        # Create DB record
        pv = PromptVersion(
            template_id=template_id,
            version_number=next_v,
            prompt_blob_path=blob_path,
            trigger_reason=trigger,
            correction_blob_path=corrections # In a real system, might save this large text to blob too
        )
        self.db.add(pv)
        
        # Update template's current version
        template.current_prompt_version = next_v
        template.optimized_prompt_blob_path = blob_path
        
        self.db.commit()
        self.db.refresh(pv)
        logger.info(f"New prompt version created: {next_v}", extra={"template": template.document_type})
        return pv

    def get_latest_prompt(self, template_id: str) -> Dict[str, Any]:
        """
        Downloads and returns the latest modular prompt structure.
        Includes a robust fallback if no prompt version exists.
        """
        template = self.db.query(PromptTemplate).filter(PromptTemplate.id == template_id).first()
        
        # Fallback if no prompt path is set yet
        if not template or not template.optimized_prompt_blob_path:
            logger.info(f"No prompt version found for template {template_id}. Using generic fallback.")
            return {
                "version": "v0",
                "template_name": template.name if template else "Default",
                "document_type": template.document_type if template else "generic",
                "system_instruction": "Extract all significant financial metrics and data tables.",
                "previous_corrections": ""
            }
            
        try:
            return self.blob_service.download_json(template.optimized_prompt_blob_path)
        except Exception as e:
            logger.warning(f"Failed to download prompt from blob {template.optimized_prompt_blob_path}: {e}. Using fallback.")
            return {
                "version": "v0",
                "template_name": template.name,
                "document_type": template.document_type,
                "system_instruction": "Extract all significant financial metrics and data tables.",
                "previous_corrections": ""
            }

    def assemble_full_prompt(self, modular_prompt: Dict[str, Any], content: str) -> str:
        """Combines modular components into a single string for the LLM."""
        lines = []
        
        # Always include the global rules
        lines.append(GLOBAL_FINANCIAL_RULES)
        
        # Use refined system instruction if available, otherwise fallback to template default
        sys_inst = modular_prompt.get("system_instruction")
        if sys_inst:
            lines.append(f"SYSTEM INSTRUCTIONS:\n{sys_inst}")
            
        if modular_prompt.get("previous_corrections"):
            lines.append(f"LEARNING FROM PREVIOUS ERRORS:\n{modular_prompt['previous_corrections']}")
            
        lines.append("SOURCE CONTENT (MARKDOWN):")
        lines.append(content)
        
        # If we have a user goal, emphasize it
        if modular_prompt.get("user_goal"):
            lines.append(f"\nFINAL GOAL: {modular_prompt['user_goal']}")
            
        lines.append("\nReturn ONLY valid JSON matching the requested structure.")
        
        # FINAL REMINDER: Traceability is mandatory
        lines.append("\nCRITICAL FINAL REMINDER:\nEvery single field must follow the 'Source Traceability' rule (Rule 5). Use the wrapper: {\"value\": ..., \"source_ref\": \"ref_N\"}. Do NOT skip this.")
        
        return "\n\n".join(lines)
