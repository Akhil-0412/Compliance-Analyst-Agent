import re

ARTICLE_PATTERN = re.compile(r"(Article\s+\d+[A-Za-z0-9()\-]*)", re.IGNORECASE)

def validate_citations(summary: str, reasoning_map: list):
    cited = set(m.group(1) for m in ARTICLE_PATTERN.finditer(summary))

    # Normalize: remove "Article", "Art.", whitespace, lower case, and trailing punctuation
    def normalize(text):
        # Remove prefix
        s = re.sub(r"^(article|art\.?)\s*", "", text.strip(), flags=re.IGNORECASE).lower()
        # Remove trailing punctuation (specifically ) or .)
        s = s.rstrip(").,")
        return s

    cited_normalized = {normalize(c) for c in cited}
    allowed_normalized = {normalize(node.article) for node in reasoning_map}

    illegal = set()
    for c in cited_normalized:
        # Allow partial match: cited "17(3)" vs allowed "17" OR cited "17" vs allowed "17(3)"
        if not any(c.startswith(a) or a.startswith(c) for a in allowed_normalized):
             illegal.add(c)

    if illegal:
        raise ValueError(f"Citation laundering detected: {illegal}")
