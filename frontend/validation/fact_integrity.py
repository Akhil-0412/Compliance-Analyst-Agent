from difflib import SequenceMatcher

def fuzzy_match(a: str, b: str) -> float:
    a_lower = a.lower()
    b_lower = b.lower()
    if a_lower in b_lower:
        return 1.0
    return SequenceMatcher(None, a_lower, b_lower).ratio()

def validate_facts(reasoning_map: list, user_query: str, threshold: float = 0.6):
    for node in reasoning_map:
        score = fuzzy_match(node.fact, user_query)
        if score < threshold:
            raise ValueError(
                f"Hallucinated fact detected: '{node.fact}' (score={score})"
            )
