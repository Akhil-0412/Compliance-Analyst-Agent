# agent/router.py

def needs_multi_article_reasoning(query: str) -> bool:
    """
    Heuristic to determine if a query likely involves cross-referencing
    between obligations (Chapter IV) and sanctions (Chapter VIII).
    """
    keywords = [
        "fine",
        "penalty",
        "maximum",
        "sanction",
        "liable",
        "consequence",
        "breach"
    ]
    
    return any(k in query.lower() for k in keywords)