import re
from typing import Tuple, Dict

PII_PATTERNS = {
    "EMAIL": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    "PHONE": r"\b(?:\+?\d{1,3}[\s-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b",
    "SSN": r"\b\d{3}-\d{2}-\d{4}\b",
    "CREDIT_CARD": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
    "IP_ADDRESS": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
    "DOB": r"\b(?:0[1-9]|1[0-2])/(?:0[1-9]|[12]\d|3[01])/(?:19|20)\d{2}\b",
    "NAME_WITH_TITLE": r"\b(Mr|Ms|Mrs|Dr|Prof)\.?\s+[A-Z][a-z]+(?:\s[A-Z][a-z]+)?\b",
}

def redact_pii(text: str) -> Tuple[str, Dict[str, str]]:
    """
    Returns:
      - redacted_text: safe to send to LLMs
      - pii_map: internal-only mapping for audits/debug
    """
    pii_map = {}
    redacted_text = text

    for label, pattern in PII_PATTERNS.items():
        matches = re.findall(pattern, redacted_text)
        for idx, match in enumerate(matches):
            placeholder = f"[REDACTED_{label}_{idx}]"
            pii_map[placeholder] = match
            redacted_text = redacted_text.replace(match, placeholder)

    return redacted_text, pii_map
