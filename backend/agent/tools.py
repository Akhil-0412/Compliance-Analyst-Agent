"""
Agent Tools — External tools the LLM can invoke during reasoning.
Implements the ReAct (Reasoning + Acting) pattern.
"""
import json
import os


# --- Tool Registry ---
TOOL_REGISTRY = {}


def register_tool(func):
    """Decorator to register a function as an available tool."""
    TOOL_REGISTRY[func.__name__] = func
    return func


# ============================================================
# TOOL: search_regulations
# ============================================================
@register_tool
def search_regulations(query: str, jurisdiction: str = "GDPR") -> str:
    """
    Search local regulation JSON for relevant articles matching the query.
    Returns the full text of matching articles.

    Args:
        query: Keywords or concepts to search for (e.g. "data breach notification")
        jurisdiction: The regulatory framework to search in ("GDPR", "CCPA", "FDA")
    """
    data_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "data", "processed", "gdpr_structured.json"
    )

    if not os.path.exists(data_path):
        return f"Error: Regulation data file not found at {data_path}"

    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    articles = data.get("articles", [])
    if not articles:
        return "Error: No articles found in regulation data."

    # Keyword search over article titles and clause texts
    query_terms = [t.lower() for t in query.split() if len(t) > 2]
    scored_articles = []

    for art in articles:
        title = art.get("title", "").lower()
        full_text = title

        for clause in art.get("clauses", []):
            full_text += " " + clause.get("text", "").lower()

        # Score = number of query terms found in the article
        score = sum(1 for term in query_terms if term in full_text)

        if score > 0:
            # Build readable article text
            article_text = f"Article {art['article_id']}: {art.get('title', 'Untitled')}\n"
            for clause in sorted(art.get("clauses", []), key=lambda c: c.get("clause_id", "")):
                article_text += f"  [{clause['clause_id']}] {clause['text']}\n"
            scored_articles.append((score, article_text))

    if not scored_articles:
        return f"No articles found matching '{query}' in {jurisdiction} regulations."

    # Return top 3 most relevant articles
    scored_articles.sort(key=lambda x: x[0], reverse=True)
    results = [text for _, text in scored_articles[:3]]

    return f"--- {jurisdiction} Regulation Search Results ---\n\n" + "\n\n".join(results)


# ============================================================
# Tool Schema for LLM Binding
# ============================================================
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_regulations",
            "description": (
                "Search local regulatory databases for specific legal articles and clauses. "
                "Use this when you need to look up the exact text of a regulation before answering. "
                "ALWAYS use this tool when the query references specific articles or when you're unsure of the exact legal text."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Keywords or article numbers to search for (e.g. 'Article 33 breach notification' or 'data erasure rights')"
                    },
                    "jurisdiction": {
                        "type": "string",
                        "enum": ["GDPR", "CCPA", "FDA"],
                        "description": "Which regulatory framework to search in."
                    }
                },
                "required": ["query"]
            }
        }
    }
]


def execute_tool_call(tool_name: str, arguments: dict) -> str:
    """
    Dispatches a tool call to the registered function.
    Returns the tool result as a string.
    """
    func = TOOL_REGISTRY.get(tool_name)
    if not func:
        return f"Error: Unknown tool '{tool_name}'"

    try:
        return func(**arguments)
    except Exception as e:
        return f"Error executing tool '{tool_name}': {str(e)}"
