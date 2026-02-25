from enum import Enum
from pydantic import BaseModel

class DecisionStatus(str, Enum):
    AUTO_APPROVED = "auto_approved"
    REVIEW_REQUIRED = "review_required"
    BLOCKED = "blocked"

class GovernanceDecision(BaseModel):
    status: DecisionStatus
    reason: str
    confidence: float
    risk_level: str