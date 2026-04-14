from typing import Any, Dict, Optional
from pydantic import BaseModel

class MasterDataResolveRequest(BaseModel):
    """
    Schema for resolving a validation conflict or failure.
    """
    action: str  # "accept", "reject", "edit"
    resolved_data: Optional[Dict[str, Any]] = None # Full JSON object if 'edit' 
