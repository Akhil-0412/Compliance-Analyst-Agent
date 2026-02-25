from reasoning.schema import AnalysisOutput

def enforce_reasoning(llm_response) -> AnalysisOutput:
    """
    llm_response is already structured via instructor / json schema.
    If parsing fails, we reject.
    """
    return AnalysisOutput.model_validate(llm_response)
