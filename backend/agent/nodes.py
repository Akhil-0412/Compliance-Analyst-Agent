"""
LangGraph Nodes — Each function takes AgentState, returns a partial state update.
Decomposed from the monolithic ComplianceAgent._analyze_logic().
"""
import re
import json
from agent.state import AgentState
from agent.llm_client import get_llm_client, safe_api_call
from agent.schemas import ComplianceResponse, RiskLevel, ReasoningMapEntry, ClarificationResponse
from agent.router import needs_multi_article_reasoning
from governance.engine import classify_decision, DecisionStatus
from retrieval.context_builder import ContextBuilder
from retrieval.indexer import ClauseIndexer

# --- Lazy LLM client (initialized on first use) ---
_llm_cache = {}


def _get_clients():
    """Lazy-init the LLM clients — only called when a node actually needs the LLM."""
    if not _llm_cache:
        base, instr, models, provider = get_llm_client()
        _llm_cache["base"] = base
        _llm_cache["instructor"] = instr
        _llm_cache["models"] = models
        _llm_cache["provider"] = provider
    return _llm_cache["base"], _llm_cache["instructor"], _llm_cache["models"]

# --- Prompts (extracted from analyst.py) ---
PROMPTS = {
    "GDPR": (
        "You are an Agentic Compliance Analyst acting as a Virtual Compliance Officer.\n"
        "Your primary obligation is legal precision. You MUST follow this reasoning sequence exactly:\n\n"
        "STEP 1: IDENTIFY FACTS. List every factual element from the user query.\n"
        "STEP 2: MAP EACH FACT to a specific GDPR subsection. One fact = one subsection.\n"
        "STEP 3: FILL the 'reasoning_map' FIRST. This is your ground truth.\n"
        "   MAPPINGS for Art 83(2): (c)=Mitigation/Actions, (f)=Cooperation, (b)=Intent/Negligence.\n"
        "   DO NOT cite 83(2)(h) for subject notification.\n"
        "STEP 4: DERIVE PROSE FROM MAP.\n"
        "   Your 'summary' and 'legal_basis' MUST only cite subsections that appear in your reasoning_map.\n"
        "   If a subsection is not in the map, you CANNOT cite it in prose.\n"
        "STEP 5: SET RISK. Use the number and severity of mapped subsections.\n"
        "   Definitions = LOW. Breaches = HIGH. Single-article questions = MEDIUM.\n\n"
        "PRECONDITION MATRIX:\n"
        "Before adjudicating, evaluate if the user query provides enough context.\n"
        "If critical modifiers are missing (encryption status, controller/processor role, data volume),\n"
        "set needs_clarification=True, populate missing_preconditions with specific questions,\n"
        "and set risk_level to 'medium' with a low confidence_score.\n\n"
        "Your output MUST be valid JSON matching the ComplianceResponse schema:\n"
        "- summary: Legal analysis.\n"
        "- legal_basis: Specific articles cited.\n"
        "- scope_limitation: Precise limits.\n"
        "- risk_analysis: Brief justification of risk.\n"
        "- needs_clarification: true if missing context prevents adjudication.\n"
        "- missing_preconditions: list of clarifying questions to ask.\n"
    ),
    "FDA": (
        "You are a Senior FDA Regulatory Consultant. "
        "Your goal is to provide guidance on US Food & Drug Administration regulations and recent legal precedents.\n\n"
        "Rules of Engagement:\n"
        "1. Focus on 21 CFR, FD&C Act, and recent court cases.\n"
        "2. Use the provided External Search Context to cite real lawsuits.\n"
        "3. Your output must strictly follow the JSON schema provided.\n"
    ),
    "CCPA": (
        "You are a Senior Privacy Counsel specializing in CCPA/CPRA. "
        "Your goal is to provide definitive, legally precise classifications based on California Civil Code.\n\n"
        "Rules of Engagement:\n"
        "1. Every claim must cite a specific CCPA section (e.g., §1798.140(v)(1)).\n"
        "2. 'Selling' and 'Sharing' are DISTINCT legal actions with separate opt-out rights.\n"
        "3. Always check for statutory exceptions (§1798.145) before classifying risk.\n"
        "4. RISK CALIBRATION: Informational/Recall questions are LOW RISK. Only actionable selling/sharing is MH/HR.\n"
        "5. Your output must strictly follow the JSON schema provided.\n"
    ),
}


# ============================================================
# NODE: Guardrail
# ============================================================
def node_guardrail(state: AgentState) -> dict:
    """
    Intent filter + routing. Determines if the query is:
    - 'blocked' (unethical evasion)
    - 'general' (small talk)
    - 'analysis' (compliance question)
    """
    query = state["user_query"]
    q_lower = query.lower()

    # --- Unethical intent filter ---
    unethical_keywords = ["evade", "bypass", "avoid detection", "hide", "loophole", "how can i hide"]
    if any(k in q_lower for k in unethical_keywords):
        blocked_response = ComplianceResponse(
            risk_level=RiskLevel.HIGH,
            confidence_score=1.0,
            legal_basis="GDPR Art 5(1)(a) (Lawfulness & Transparency)",
            summary=(
                "This request involves evasion of mandatory compliance obligations. "
                "Attempting to hide data breaches violates Article 33 (Notification Authority) "
                "and Article 34 (Notification to Data Subject)."
            ),
            scope_limitation="N/A - Illegal Request",
            risk_analysis="Severe regulatory fines (up to 4% global turnover) and criminal liability.",
            reasoning_map=[],
        )
        return {
            "route": "blocked",
            "final_response": blocked_response.model_dump(),
        }

    # --- General conversation check ---
    general_triggers = ["hi", "hello", "who are you", "what can you do", "help", "thanks", "good morning", "capabilities"]
    is_general = len(query.split()) < 10 and any(t in q_lower for t in general_triggers)

    if is_general:
        return {"route": "general"}

    return {"route": "analysis"}


# ============================================================
# NODE: Chat (General Conversation)
# ============================================================
def node_chat(state: AgentState) -> dict:
    """Handles general conversation (greetings, capabilities)."""
    messages = [
        {"role": "system", "content": (
            "You are the 'Agentic Compliance Analyst', an advanced AI specialized in global regulations. "
            "You have deep knowledge of GDPR (EU), FDA (US), and are expanding to Global Compliance. "
            "Introduce yourself formally and list your capabilities (searching laws, analyzing risk, drafting reports). "
            "Do not answer specific compliance questions here; just introduce yourself."
        )},
        {"role": "user", "content": state["user_query"]},
    ]

    base, instr, models = _get_clients()
    response = safe_api_call(base, instr, models, messages, temperature=0.7)
    chat_text = response.choices[0].message.content

    return {"final_response": {"type": "chat", "message": chat_text}}


# ============================================================
# NODE: Retrieve (FAISS + Context Builder)
# ============================================================
def node_retrieve(state: AgentState) -> dict:
    """Performs FAISS hybrid search and builds the legal context string."""
    domain = state["domain"]
    query = state["user_query"]

    if domain == "GDPR":
        from retrieval.indexer import ClauseIndexer
        import json as _json

        data_path = "data/processed/gdpr_structured.json"
        context_builder = ContextBuilder(data_path)

        # Build FAISS indexer
        indexer = ClauseIndexer()
        with open(data_path, "r", encoding="utf-8") as f:
            data = _json.load(f)
            texts, metadata = [], []
            if "articles" in data:
                for art in data["articles"]:
                    for clause in art.get("clauses", []):
                        texts.append(clause["text"])
                        metadata.append({
                            "article_id": art["article_id"],
                            "clause_id": clause["clause_id"],
                            "text": clause["text"],
                        })
            if texts:
                indexer.build(texts, metadata)

        is_complex = needs_multi_article_reasoning(query)
        k = 6 if is_complex else 3
        results = indexer.hybrid_search(query, k=k)

        if not results:
            return {
                "retrieved_context": "",
                "final_response": {"type": "error", "message": "Insufficient context found."},
                "route": "blocked",
            }

        retrieved_ids = {str(r["article_id"]) for r in results}
        q_lower = query.lower()

        # Domain logic injection
        DOMAIN_MAP = {
            "penalty_logic": {"triggers": ["fine", "penalty", "administrative", "sanction", "euro"], "inject": ["83"]},
            "scope_logic": {"triggers": ["apply", "applies", "scope", "territorial", "material", "when does"], "inject": ["2", "3"]},
            "definition_logic": {"triggers": ["define", "definition", "meaning", "what is a", "who is a"], "inject": ["4"]},
            "rights_logic": {"triggers": ["delete", "erasure", "erase", "forget", "access", "rectify", "copy"], "inject": ["6", "12", "15", "17"]},
            "dpo_logic": {"triggers": ["dpo", "officer", "representative", "public authority"], "inject": ["37", "38", "39"]},
            "transfer_logic": {"triggers": ["transfer", "third country", "abroad", "adequacy"], "inject": ["45", "46", "49"]},
        }
        for _domain, rules in DOMAIN_MAP.items():
            if any(t in q_lower for t in rules["triggers"]):
                for art_id in rules["inject"]:
                    retrieved_ids.add(art_id)

        full_contexts = [context_builder.expand_article_by_id(aid) for aid in sorted(list(retrieved_ids))]
        combined_context = "\n\n".join(full_contexts)

    elif domain == "FDA":
        from agent.tavily_search import LawsuitSearcher
        tavily = LawsuitSearcher()
        combined_context = tavily.search_lawsuits(query)

    elif domain == "CCPA":
        combined_context = "Source: CCPA/CPRA Legal Statutes (Modeled Knowledge - Statutory Exception Active)."
    else:
        combined_context = ""

    return {"retrieved_context": combined_context}


# ============================================================
# NODE: Clarify (Detects ambiguity, generates follow-up options)
# ============================================================
CLARIFY_PROMPT = """You are a regulatory analysis assistant. Given the user's query and the retrieved legal context, determine:
1. Is this query CLEAR enough to give a confident regulatory answer? Or does the answer DEPEND on additional context?

A query is CLEAR if:
- It asks about a definition (e.g., "What is personal data?")
- It refers to a specific article or regulation
- The context provides enough information to answer confidently

A query DEPENDS on context if:
- The answer varies significantly based on circumstances (e.g., "We lost patient data" — depends on whether data was encrypted, how many records, whether authorities were notified)
- Critical facts are missing that would change the risk level or legal outcome

If it DEPENDS, generate 3-4 high-quality follow-up options ranked by importance, that would help narrow down the analysis. Each option should be a specific, actionable clarification question.

IMPORTANT: Respond with JSON matching the schema exactly. If the query is clear, set needs_clarification=false and options=[]."""

def node_clarify(state: AgentState) -> dict:
    """
    Lightweight LLM call to check if a query needs clarification.
    If user already provided selections from a previous turn, skip clarification.
    """
    # If user already answered clarification questions, skip to LLM
    user_selections = state.get("user_selections")
    if user_selections:
        # Enrich the context with user's answers
        enriched = state.get("retrieved_context", "") + "\n\n[USER CLARIFICATION]\n"
        enriched += "\n".join(f"- {sel}" for sel in user_selections)
        return {"retrieved_context": enriched, "route": "clear"}

    query = state["user_query"]
    context = state.get("retrieved_context", "")
    domain = state["domain"]

    # Skip clarification for simple definition queries
    definition_keywords = ["what is", "define", "meaning of", "article", "section", "explain"]
    if any(kw in query.lower() for kw in definition_keywords):
        return {"route": "clear"}

    try:
        base, instr, models = _get_clients()

        messages = [
            {"role": "system", "content": CLARIFY_PROMPT},
            {"role": "user", "content": f"Domain: {domain}\nQuery: {query}\nContext Preview: {context[:500]}"},
        ]

        result: ClarificationResponse = safe_api_call(
            base, instr, models, messages,
            temperature=0, response_model=ClarificationResponse,
        )

        if not result.needs_clarification or not result.options:
            return {"route": "clear"}

        # Build the options list with static entries appended
        options = [opt.model_dump() for opt in result.options[:4]]

        # Add "Other" free-text option
        options.append({
            "id": "opt_custom",
            "text": "Other (describe your situation)",
            "rank": 5,
        })

        # Add "I don't know" option
        options.append({
            "id": "opt_unknown",
            "text": "I don't know / Skip clarification",
            "rank": 6,
        })

        return {
            "route": "depends",
            "clarification_options": options,
            "final_response": {
                "type": "clarification",
                "summary": result.summary,
                "options": options,
            },
        }

    except Exception as e:
        # On failure, skip clarification and proceed to LLM
        print(f"[CLARIFY] Error: {e}, skipping clarification")
        return {"route": "clear"}


def route_after_clarify(state: AgentState) -> str:
    """Routes to LLM if clear, or END if clarification is needed."""
    route = state.get("route", "clear")
    if route == "depends":
        return "end"
    return "llm"


# ============================================================
# NODE: LLM (Structured Generation)
# ============================================================
def node_llm(state: AgentState) -> dict:
    """
    Calls the LLM with the system prompt + retrieved context.
    On retry, appends validation errors to the conversation.
    """
    domain = state["domain"]
    query = state["user_query"]
    context = state.get("retrieved_context", "")
    retry_count = state.get("retry_count", 0)
    prev_errors = state.get("validation_errors", [])

    # Risk guidance for definition queries
    is_definition_query = any(k in query.lower() for k in [
        "what is", "define", "meaning of", "considered personal info", "stand for", "are ip addresses"
    ])
    risk_guidance = ""
    if is_definition_query:
        risk_guidance = "\n[CONTEXT NOTE: This is a DEFINITION query. Risk Level must be 'low'. Calibrate confidence to 1.0.]"

    system_prompt = PROMPTS.get(domain, PROMPTS["GDPR"])

    # Build messages
    messages = [
        {"role": "system", "content": system_prompt + risk_guidance},
        {"role": "user", "content": f"CONTEXT (Source: {domain} Knowledge):\n{context}\n\nQUERY: {query}"},
    ]

    # If this is a retry, inject the previous errors
    if retry_count > 0 and prev_errors:
        prev_analysis = state.get("analysis")
        if prev_analysis:
            messages.append({"role": "assistant", "content": json.dumps(prev_analysis)})
        error_text = "\n".join(prev_errors)
        messages.append({
            "role": "user",
            "content": (
                f"CRITICAL LOGIC ERROR: Your previous answer failed validation rules.\n"
                f"Errors:\n{error_text}\n\n"
                f"FIX IMMEDIATELY. Cite the missing articles. Correct the scope."
            ),
        })

    try:
        base, instr, models = _get_clients()
        structured_response: ComplianceResponse = safe_api_call(
            base, instr, models, messages,
            temperature=0, response_model=ComplianceResponse,
        )

        if isinstance(structured_response, str):
            return {
                "final_response": {"type": "error", "message": structured_response},
                "route": "blocked",
            }

        return {
            "analysis": structured_response.model_dump(),
            "validation_errors": [],  # Clear previous errors
            "messages": messages,
        }

    except Exception as e:
        return {
            "final_response": {"type": "error", "message": f"API Error: {str(e)}"},
            "route": "blocked",
        }


# ============================================================
# NODE: Validator
# ============================================================
def node_validator(state: AgentState) -> dict:
    """
    Runs all validation rules on the generated analysis.
    Returns validation_errors list (empty = PASS).
    """
    analysis_dict = state.get("analysis")
    if not analysis_dict:
        return {"validation_errors": ["No analysis to validate."]}

    query = state["user_query"]
    retry_count = state.get("retry_count", 0)

    try:
        response = ComplianceResponse(**analysis_dict)
    except Exception as e:
        return {
            "validation_errors": [f"Failed to parse analysis: {str(e)}"],
            "retry_count": retry_count + 1,
        }

    errors = _validate_response(response, query)

    if errors:
        return {
            "validation_errors": errors,
            "retry_count": retry_count + 1,
        }

    return {"validation_errors": []}


def _validate_response(response: ComplianceResponse, query: str) -> list[str]:
    """
    Validates the compliance response against strict rules.
    Returns a list of error strings (empty = all passed).
    """
    errors = []
    q_lower = query.lower()

    # --- RULE 0: REASONING_MAP VALIDATION ---
    if not response.reasoning_map or len(response.reasoning_map) == 0:
        errors.append("❌ Reasoning Map: The reasoning_map field is EMPTY. You MUST populate it.")
    else:
        map_subsections = {entry.gdpr_subsection for entry in response.reasoning_map}
        prose_text = response.summary + " " + response.legal_basis
        prose_subsections = set(re.findall(r"\d+\(\d+\)\([a-z]\)", prose_text))

        orphan_subsections = prose_subsections - map_subsections
        if orphan_subsections:
            errors.append(f"❌ Citation Laundering: {orphan_subsections} cited in prose but NOT in reasoning_map.")

        for entry in response.reasoning_map:
            subsection = entry.gdpr_subsection.lower()
            combined_text = (entry.legal_meaning + " " + entry.justification + " " + entry.fact).lower()

            if "83(2)(h)" in subsection:
                errors.append("❌ Subsection Error: Do not cite 83(2)(h) for notification. Use 83(2)(c).")

            if "83(2)(c)" in subsection:
                authority_keywords = ["authority", "regulator", "investigat", "supervis", "cooperat"]
                data_subject_keywords = ["data subject", "affected", "harm", "damage", "protect", "inform"]
                if any(w in combined_text for w in authority_keywords) and not any(w in combined_text for w in data_subject_keywords):
                    errors.append(f"❌ Semantic Split: 83(2)(c) is for data subjects, not authority cooperation.")

            if "83(2)(f)" in subsection:
                if not any(w in combined_text for w in ["authority", "regulator", "investigat", "supervis", "cooperat"]):
                    errors.append(f"❌ Semantic Mismatch: 83(2)(f) must describe cooperation with authority.")

            # Fact integrity check
            fact_key_terms = [t for t in entry.fact.lower().split() if len(t) > 4 and t not in ["which", "their", "about", "after", "before", "under", "where"]]
            fact_grounded = any(term in q_lower for term in fact_key_terms)
            if not fact_grounded and len(fact_key_terms) > 0:
                errors.append(f"❌ Fact Integrity: '{entry.fact}' not grounded in user query.")

    # --- LEGACY RULES ---
    if "erase" in q_lower or "deletion" in q_lower or "force" in q_lower:
        if "17" not in response.legal_basis and "17" not in response.summary:
            errors.append("❌ Citation Integrity: Erasure/deletion discussed but Article 17 not cited.")
        if "6" not in response.legal_basis and "6" not in response.summary:
            errors.append("❌ Legal Basis Missing: Must cite Article 6 (Lawfulness).")

    if "17(3)(b)" in response.legal_basis or "legal obligation" in response.legal_basis.lower():
        if "strictly necessary" not in response.scope_limitation.lower():
            errors.append("❌ Scope Logic: When claiming 'legal obligation', must state 'strictly necessary'.")

    if "partial refusal" in response.summary.lower() and response.risk_level == RiskLevel.LOW:
        errors.append("❌ Risk Signal: Partial Refusals must be MEDIUM or HIGH, not LOW.")

    if "fine" in q_lower or "mitigat" in q_lower or "83" in response.legal_basis:
        if response.risk_level == RiskLevel.LOW:
            errors.append("❌ Risk Signal: Mitigation implies infringement. Risk cannot be LOW.")

        factors = ["nature", "gravity", "duration", "negligen", "intentional", "actions taken", "mitigat", "cooperate", "cooperation", "categories", "previous infringement", "notify", "notified"]
        found_factors = [f for f in factors if f in response.summary.lower()]
        if len(found_factors) < 3:
            errors.append(f"❌ Depth Check: Art 83(2) requires multi-factor test. Only {len(found_factors)} found.")

        subsection_matches = re.findall(r"83\(2\)\([a-k]\)", response.summary)
        if len(subsection_matches) < 2:
            errors.append("❌ Subsection Grounding: Must cite at least two 83(2) subsections.")

    return errors


# ============================================================
# NODE: Semantic Override (Python-Layer Corrections)
# ============================================================
def node_semantic_override(state: AgentState) -> dict:
    """Applies hard-coded semantic corrections that the LLM cannot be trusted with."""
    analysis_dict = state.get("analysis")
    if not analysis_dict:
        return {}

    response = ComplianceResponse(**analysis_dict)
    domain = state["domain"]
    query = state["user_query"]
    q_lower = query.lower()

    is_definition_query = any(k in q_lower for k in [
        "what is", "define", "meaning of", "considered personal info", "stand for", "are ip addresses"
    ])

    if domain == "GDPR":
        if "tax" in q_lower and ("erase" in q_lower or "delet" in q_lower or "refuse" in q_lower):
            response.risk_level = RiskLevel.MEDIUM
            response.confidence_score = 1.0
            response.legal_basis = "GDPR Article 17(3)(b) (Exception) & Article 6(1)(c) (Lawful Basis)"
            response.scope_limitation = "Only personal data strictly necessary for the legal obligation may be retained. All other personal data must be erased."
            response.summary = (
                "Partial Refusal. Under GDPR Article 17(3)(b), the right to erasure does not apply where processing is necessary "
                "to comply with a legal obligation. Retention of transaction records required by tax law is lawful under Article 6(1)(c). "
                "However, only data strictly necessary for the obligation may be retained; all other data must be erased."
            )

    elif domain == "CCPA":
        SEMANTIC_MAP = {
            "personal information": ("§1798.140(v)(1)", RiskLevel.LOW, 1.0),
            "sensitive": ("§1798.140(ae)", RiskLevel.MEDIUM, 0.95),
            "sale": ("§1798.140(ad)", RiskLevel.MEDIUM, 0.95),
            "share": ("§1798.140(ah)", RiskLevel.MEDIUM, 0.95),
            "fraud": ("§1798.105(d)(1)", RiskLevel.MEDIUM, 0.90),
            "delete": ("§1798.105", RiskLevel.MEDIUM, 0.90),
            "geolocation": ("§1798.140(ae)", RiskLevel.MEDIUM, 0.95),
        }
        for key, (citation, risk, conf) in SEMANTIC_MAP.items():
            if key in q_lower:
                response.legal_basis = f"California Civil Code {citation}"
                response.risk_level = risk
                response.confidence_score = conf
                break

    # Definition query override
    if is_definition_query and response.risk_level != RiskLevel.HIGH:
        response.confidence_score = 1.0
        response.risk_level = RiskLevel.LOW

    return {"analysis": response.model_dump()}


# ============================================================
# NODE: Governance (Decision Gate)
# ============================================================
def node_governance(state: AgentState) -> dict:
    """Runs the governance engine to classify the decision."""
    analysis_dict = state.get("analysis")
    if not analysis_dict:
        return {"final_response": {"type": "error", "message": "No analysis for governance."}}

    response = ComplianceResponse(**analysis_dict)

    # Fast exit for clarification
    if response.needs_clarification:
        return {"final_response": response.model_dump()}

    decision = classify_decision(
        confidence=response.confidence_score,
        risk_level=response.risk_level.value,
        requires_refusal=False,
    )

    if decision.status == DecisionStatus.BLOCKED:
        return {"final_response": {"type": "blocked", "reason": decision.reason}}

    if decision.status == DecisionStatus.REVIEW_REQUIRED:
        return {
            "final_response": {
                "type": "review_required",
                "reason": decision.reason,
                "risk_level": decision.risk_level,
                "confidence": decision.confidence,
                **response.model_dump(),
            }
        }

    # AUTO_APPROVED
    return {"final_response": response.model_dump()}


# ============================================================
# NODE: Tool Executor (ReAct Pattern)
# ============================================================
def node_tool_executor(state: AgentState) -> dict:
    """
    Executes pending tool calls from the LLM and appends results
    to the message history. Routes back to LLM for final answer.
    """
    from agent.tools import execute_tool_call

    tool_calls = state.get("tool_calls", [])
    new_messages = []

    for tc in tool_calls:
        tool_name = tc.get("name", "")
        arguments = tc.get("arguments", {})

        print(f"[TOOL] Executing tool: {tool_name}({arguments})")
        result = execute_tool_call(tool_name, arguments)

        new_messages.append({
            "role": "tool",
            "content": result,
            "name": tool_name,
        })

    return {
        "messages": new_messages,
        "tool_calls": [],  # Clear pending tool calls
    }


# ============================================================
# NODE: Fallback (Max Retries Exceeded)
# ============================================================
def node_fallback(state: AgentState) -> dict:
    """Returns a hard failure after exhausting all retries."""
    errors = state.get("validation_errors", [])
    return {
        "final_response": {
            "type": "error",
            "message": f"❌ Analysis failed after {state.get('retry_count', 0)} retries. Last errors: {errors}",
        }
    }


# ============================================================
# ROUTING FUNCTIONS (Conditional Edges)
# ============================================================
def route_after_guardrail(state: AgentState) -> str:
    """Routes based on guardrail classification."""
    route = state.get("route", "analysis")
    if route == "blocked":
        return "end"
    elif route == "general":
        return "chat"
    return "retrieve"


def route_after_llm(state: AgentState) -> str:
    """Routes after LLM: tool call, blocked error, or validation."""
    if state.get("route") == "blocked":
        return "end"
    tool_calls = state.get("tool_calls", [])
    if tool_calls:
        return "tool_executor"
    return "validator"


def route_after_validation(state: AgentState) -> str:
    """Routes after validation: pass, retry, or fallback."""
    errors = state.get("validation_errors", [])
    retry_count = state.get("retry_count", 0)

    if not errors:
        return "semantic_override"
    elif retry_count < 3:
        return "llm"
    else:
        return "fallback"
