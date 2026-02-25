from governance.decision import GovernanceDecision, DecisionStatus

def classify_decision(
    confidence: float,
    risk_level: str = "medium",
    requires_refusal: bool = False
) -> GovernanceDecision:
    """
    Deterministically decides if an AI response is safe to show,
    needs human eyes, or must be blocked entirely.
    """

    # 1. Absolute Block (Safety/Policy Violation)
    if requires_refusal:
        return GovernanceDecision(
            status=DecisionStatus.BLOCKED,
            reason="Response flagged as policy violation or refusal required.",
            confidence=confidence,
            risk_level=risk_level
        )

    # 2. Critical Risk Gates (Always Human Review)
    # Examples: Penalties, Cross-Border Transfers, High-Stakes Fines
    if risk_level == "critical":
        return GovernanceDecision(
            status=DecisionStatus.REVIEW_REQUIRED,
            reason="Critical risk topic (e.g., Penalties) mandates human oversight.",
            confidence=confidence,
            risk_level=risk_level
        )

    # 3. Confidence Gates (AI Uncertainty)
    # Calibrated threshold from Phase 4.2
    if confidence < 0.75:
        return GovernanceDecision(
            status=DecisionStatus.REVIEW_REQUIRED,
            reason=f"Low model confidence ({confidence:.2f}).",
            confidence=confidence,
            risk_level=risk_level
        )

    # 4. Safe to Proceed
    return GovernanceDecision(
        status=DecisionStatus.AUTO_APPROVED,
        reason="Confidence and risk levels within safe autonomous limits.",
        confidence=confidence,
        risk_level=risk_level
    )