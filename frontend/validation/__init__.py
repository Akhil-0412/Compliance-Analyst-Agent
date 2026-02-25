from validation.citation import validate_citations
from validation.fact_integrity import validate_facts
from validation.risk_consistency import validate_risk

def validate_all(analysis, user_query: str):
    validate_citations(analysis.summary, analysis.reasoning_map)
    validate_facts(analysis.reasoning_map, user_query)
    validate_risk(analysis.reasoning_map, analysis.risk_level)
