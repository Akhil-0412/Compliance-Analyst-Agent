from governance.policies import (
    CONFIDENCE_REVIEW_THRESHOLD,
    BLOCKING_KEYWORDS,
    HIGH_RISK_TERMS
)

def classify(analysis, query: str = "") -> str:
    # 0. Pre-emptive blocking on query
    query_lower = query.lower()
    print(f"DEBUG: Checking query '{query_lower}' against {BLOCKING_KEYWORDS}")
    for term in BLOCKING_KEYWORDS:
        if term in query_lower:
            return "BLOCKED"

    # 1. Confidence gate
    if analysis.confidence < CONFIDENCE_REVIEW_THRESHOLD:
        return "REVIEW_REQUIRED"

    summary_lower = analysis.summary.lower()

    # 2. Absolute blockers (Summary check)
    for term in BLOCKING_KEYWORDS:
        if term in summary_lower:
            return "BLOCKED"

    # 3. High-risk escalation
    if analysis.risk_level == "High":
        return "REVIEW_REQUIRED"

    for term in HIGH_RISK_TERMS:
        if term in summary_lower:
            return "REVIEW_REQUIRED"

    return "AUTO_APPROVED"
