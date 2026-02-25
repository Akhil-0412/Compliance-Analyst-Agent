from reasoning.schema import AnalysisOutput

def build_response(analysis: AnalysisOutput, decision: str) -> dict:
    """
    Constructs the final response dictionary.
    """
    return {
        "analysis": analysis,
        "decision": decision
    }
