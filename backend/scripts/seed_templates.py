import sys
import os
from sqlalchemy.orm import Session

# Add backend to path so we can import models/core
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import SessionLocal
from models.template import PromptTemplate

def seed_financial_template():
    db = SessionLocal()
    try:
        # 1. Look for existing 'financial_document' template
        template = db.query(PromptTemplate).filter_by(document_type='financial_document').first()
        
        if not template:
            print("Creating new financial_document template (lean version)...")
            template = PromptTemplate(
                name="Default Financial Extractor",
                document_type="financial_document",
                current_prompt_version="v1",
                field_mapping=[] # Explicitly empty as it's redundant now
            )
            db.add(template)
            db.commit()
            db.refresh(template)
            print(f"Successfully seeded 'financial_document' template.")
        else:
            # Check if it's already lean to avoid redundant commits
            if template.field_mapping != []:
                print("Template 'financial_document' exists but has stale field_mapping. Cleaning up...")
                template.field_mapping = []
                db.commit()
                print("Successfully updated template.")
            else:
                print("Template 'financial_document' is already optimally seeded. Skipping.")
        
    except Exception as e:
        print(f"Error seeding templates: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_financial_template()
