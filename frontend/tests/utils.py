RISK_ORDER = {
    "Low": 0,
    "Medium": 1,
    "High": 2
}

def risk_at_least(actual: str, minimum: str) -> bool:
    return RISK_ORDER[actual] >= RISK_ORDER[minimum]
