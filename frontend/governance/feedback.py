from pydantic import BaseModel
from typing import Literal

class ReviewFeedback(BaseModel):
    case_id: str
    original_decision: Literal["AUTO_APPROVED", "REVIEW_REQUIRED"]
    reviewer_decision: Literal["APPROVED", "REJECTED"]
    notes: str
