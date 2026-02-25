import re
from datetime import date

def extract_event_date(text: str) -> date | None:
    match = re.search(r"\b(20\d{2})\b", text)
    if match:
        return date(int(match.group(1)), 1, 1)
    return None
