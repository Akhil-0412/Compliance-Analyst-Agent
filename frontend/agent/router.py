import re

ENFORCEMENT_KEYWORDS = {
    "penalty", "fine", "sanction", "lawsuit",
    "enforcement", "violation", "liable"
}

REGULATION_KEYWORDS = {
    "gdpr", "ccpa", "cpra", "fda", "hipaa",
    "personal data", "data subject", "privacy",
    "breach", "security", "incident", "detect"
}

def score_complexity(text: str) -> float:
    text_lower = text.lower()

    # 1. Critical Risk Triggers (Force Max Complexity)
    crtical_keywords = {"breach", "leak", "hack", "unauthorized access", "fine", "penalty", "sanction"}
    if any(k in text_lower for k in crtical_keywords):
        return 1.0

    # 2. Intent Classification
    is_drafting = any(k in text_lower for k in {"draft", "write", "create", "generate"})
    is_definition = any(k in text_lower for k in {"what is", "define", "meaning of", "stand for"})

    if is_definition and len(text.split()) < 15:
        return 0.1 # Very simple

    # 3. Standard Complexity
    regulation_hits = sum(1 for r in REGULATION_KEYWORDS if r in text_lower)
    enforcement_hits = sum(1 for k in ENFORCEMENT_KEYWORDS if k in text_lower)
    length_score = min(len(text.split()) / 200, 1.0)
    conditional_score = 0.2 if re.search(r"\b(if|unless|provided that|where)\b", text_lower) else 0.0

    score = (
        0.35 * min(regulation_hits, 1.0) +
        0.35 * min(enforcement_hits / 2, 1.0) +
        0.2 * conditional_score +
        0.1 * length_score
    )
    
    if is_drafting:
        score += 0.2

    return round(min(score, 1.0), 2)

def route_query(text: str) -> str:
    complexity = score_complexity(text)

    # TIER 1: Simple / Definitions (Speed)
    if complexity < 0.25:
        return "llama-3-8b"
    
    # TIER 2: Moderate Reasoning (Balanced)
    elif complexity < 0.65:
        return "llama-3-70b"
    
    # TIER 3: Complex / Critical / Drafting (Power)
    else:
        # Cross-regulation or high stakes
        return "gemini-1.5-pro"
