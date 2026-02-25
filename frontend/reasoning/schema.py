from pydantic import BaseModel, Field
from typing import List, Literal
from datetime import datetime
from typing import Optional, Union, Any

class ReasoningNode(BaseModel):
    fact: str = Field(..., description="Verbatim fact from user input")
    legal_meaning: str = Field(..., description="Interpretation of the fact in legal terms")
    regulation: Literal["GDPR", "CCPA", "FDA", "IRS", "Other"] # Added 'Other' for fallback
    article: str = Field(..., description="Exact article or section reference")
    justification: str = Field(..., description="Why this fact maps to this article")
    regulation_version: Optional[str] = None
    effective_date: Optional[Union[str, Any]] = None
class AnalysisOutput(BaseModel):
    needs_clarification: bool = Field(default=False, description="Set to True if critical preconditions are missing to make a confident regulatory assessment.")
    missing_preconditions: List[str] = Field(default_factory=list, description="List of specific questions to ask the user to gather missing context (e.g., 'Was the data encrypted?').")
    reasoning_map: List[ReasoningNode]
    risk_level: Literal["Low", "Medium", "High", "Unknown"] = Field(..., description="If needs_clarification is True, risk_level should be 'Unknown'.")
    confidence: float = Field(..., ge=0.0, le=1.0)
    summary: str
