from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional, Literal, Union
from enum import Enum

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    
    @classmethod
    def _missing_(cls, value):
        """Handle case-insensitive enum matching (e.g., 'MEDIUM' -> 'medium')"""
        if isinstance(value, str):
            normalized = value.lower()
            for member in cls:
                if member.value == normalized:
                    return member
        return None


class ClarificationOption(BaseModel):
    """A single ranked follow-up option for ambiguous queries."""
    id: str = Field(..., description="Unique option ID like 'opt_1'")
    text: str = Field(..., description="The clarification question or option text")
    rank: int = Field(..., ge=1, le=4, description="Quality rank 1-4 (1=most relevant)")


class ClarificationResponse(BaseModel):
    """LLM output when it detects a query needs clarification."""
    needs_clarification: bool = Field(..., description="True if the query is ambiguous and depends on context")
    summary: str = Field(..., description="Brief explanation of why clarification is needed")
    options: List[ClarificationOption] = Field(
        default_factory=list,
        description="List of 3-4 ranked follow-up options that would help narrow down the analysis"
    )

# Normalized GDPR Subsection Tokens (Whitelist)
GDPR_SUBSECTIONS = Literal[
    # Article 83(2) - Fine Mitigation Factors
    "83(2)(a)", "83(2)(b)", "83(2)(c)", "83(2)(d)", "83(2)(e)", 
    "83(2)(f)", "83(2)(g)", "83(2)(h)", "83(2)(i)", "83(2)(j)", "83(2)(k)",
    # Article 17 - Right to Erasure
    "17(1)", "17(2)", "17(3)(a)", "17(3)(b)", "17(3)(c)", "17(3)(d)", "17(3)(e)",
    # Article 6 - Lawful Basis
    "6(1)(a)", "6(1)(b)", "6(1)(c)", "6(1)(d)", "6(1)(e)", "6(1)(f)",
    # Article 5 - Principles
    "5(1)(a)", "5(1)(b)", "5(1)(c)", "5(1)(d)", "5(1)(e)", "5(1)(f)", "5(2)",
    # Other common articles
    "4(1)", "4(2)", "4(7)", "4(8)", "33(1)", "34(1)", "45(1)", "46(1)"
]

class ReasoningMapEntry(BaseModel):
    """
    A single Fact -> Law mapping entry.
    Each entry MUST reference exactly ONE GDPR subsection.
    """
    fact: str = Field(
        ..., 
        description="A factual element explicitly stated in the user query."
    )
    legal_meaning: str = Field(
        ..., 
        description="What this fact represents legally (e.g., 'mitigation of harm', 'cooperation')."
    )
    gdpr_subsection: str = Field(
        ..., 
        description="Exact GDPR subsection (e.g., '83(2)(c)'). Must be a single, normalized token."
    )
    justification: str = Field(
        ..., 
        description="One sentence explaining why this fact satisfies the subsection."
    )
    
    @field_validator('gdpr_subsection')
    @classmethod
    def validate_single_subsection(cls, v):
        # Enforce 1:1 mapping: No commas or 'and' allowed
        if ',' in v or ' and ' in v.lower():
            raise ValueError("Each entry must reference exactly ONE subsection. Split into multiple entries.")
        return v

class ComplianceResponse(BaseModel):
    """
    Structured response for GDPR compliance analysis.
    """
    summary: str = Field(
        ..., 
        description="A concise summary of the legal situation based on the provided text."
    )
    needs_clarification: bool = Field(
        default=False, 
        description="Set to True if critical preconditions are missing to make a confident regulatory assessment."
    )
    missing_preconditions: List[str] = Field(
        default_factory=list, 
        description="List of specific questions to ask the user to gather missing context (e.g., 'Was the data encrypted?')."
    )
    legal_basis: Union[str, List[str]] = Field(
        ..., 
        description="The specific statutory basis (e.g., 'Article 6(1)(c)'). If multiple, can be a list or comma-separated string."
    )
    scope_limitation: str = Field(
        ...,
        description="The precise limits of any refusal or processing. Must include 'only data strictly necessary' if applicable."
    )
    risk_analysis: str = Field(
        ..., 
        description="Analysis of potential risks, fines, or obligations."
    )
    risk_level: RiskLevel = Field(
        ..., 
        description="The severity of the risk. Must be MEDIUM or HIGH for any partial refusal."
    )
    confidence_score: float = Field(
        default=0.5, 
        ge=0.0, 
        le=1.0, 
        description="Confidence score between 0.0 and 1.0 based on citation strength."
    )
    references: Optional[List[str]] = Field(
        default_factory=list,
        description="List of specific article IDs referenced (e.g. ['83', '28'])."
    )
    reasoning_map: List[ReasoningMapEntry] = Field(
        ...,
        description="MANDATORY: A list of Fact -> Law mappings. Every GDPR subsection cited in summary MUST appear here first."
    )

    @field_validator('risk_level', mode='before')
    @classmethod
    def normalize_risk_level(cls, v):
        if isinstance(v, str):
            # Map upper case to lower case enum values
            return v.lower()
        return v
    
    @field_validator('legal_basis', mode='before')
    @classmethod
    def normalize_legal_basis(cls, v):
        if isinstance(v, list):
            return ", ".join(v)
        return v

    @field_validator('risk_level')
    @classmethod
    def validate_risk_consistency(cls, v, info):
        return v
    @classmethod
    def validate_confidence(cls, v):
        return round(v, 2)
