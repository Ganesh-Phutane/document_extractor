"""
agents/reextraction_agent.py
────────────────────────────
Orchestrates the iterative self-correction loop.
Triggers learning (prompt update) and re-extraction until confidence >= 90%.
"""
import json
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from models.document import Document
from models.extraction import ExtractedData
from agents.extraction_agent import ExtractionAgent
from agents.verification_agent import VerificationAgent
from services.template_service import TemplateService
from core.logger import get_logger

logger = get_logger(__name__)

class ReExtractionAgent:
    def __init__(self, db: Session):
        self.db = db
        self.extraction_agent = ExtractionAgent(db)
        self.verification_agent = VerificationAgent(db)
        self.template_service = TemplateService(db)

    async def run_pipeline(self, document_id: str, user_goal: str = None, max_iterations: int = 3) -> Dict[str, Any]:
        """
        Runs the full iterative pipeline for a document.
        If user_goal is provided, it refines the goal into a system prompt first.
        """
        logger.info(f"ReExtractionAgent starting pipeline for doc: {document_id}")
        
        doc = self.db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise ValueError(f"Document {document_id} not found")

        # 0. Initial Goal Refinement (if provided)
        if user_goal:
            logger.info(f"Refining user goal: {user_goal}")
            await self.template_service.create_prompt_version_from_goal(
                template_id=doc.template_id,
                user_goal=user_goal
            )

        iteration = 0
        final_result = None
        
        while iteration < max_iterations:
            iteration += 1
            logger.info(f"Starting iteration {iteration} for doc {document_id}")
            
            # 1. Extraction
            extraction_result = await self.extraction_agent.extract(document_id)
            extraction_id = extraction_result["extraction_id"]
            
            # 2. Verification
            verification_result = self.verification_agent.verify(extraction_id)
            confidence = verification_result["confidence"]
            
            final_result = {
                "iteration": iteration,
                "confidence": confidence,
                "data": extraction_result["data"],
                "issues": verification_result["issues"]
            }
            
            # 3. Check Threshold
            if confidence >= 0.9:
                logger.info(f"Threshold reached (90%+) at iteration {iteration}")
                doc.status = "verified"
                self.db.commit()
                break
                
            # 4. Learning Phase: Update Prompt if needed
            if iteration < max_iterations:
                logger.info(f"Confidence {confidence} below 90%. Updating prompt...")
                
                # Format issues for the LLM
                correction_notes = "\n".join([
                    f"- Problem with field '{i['field_name']}': {i['message']}"
                    for i in verification_result["issues"]
                ])
                
                # Create a new version of the prompt with these corrections
                self.template_service.create_prompt_version(
                    template_id=doc.template_id,
                    trigger="reextraction_agent",
                    corrections=correction_notes
                )
                
                doc.status = "reextracting"
                self.db.commit()
            else:
                logger.warning(f"Max iterations ({max_iterations}) reached without hitting 90% threshold.")
                doc.status = "manual_review_required"
                self.db.commit()
        
        return final_result
