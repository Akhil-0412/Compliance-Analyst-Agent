from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import sys
import os
import asyncio
from sse_starlette.sse import EventSourceResponse
import json

# Add parent dir to path to import agent modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agent.analyst import ComplianceAgent
from retrieval.indexer import ClauseIndexer

app = FastAPI(title="ComplianceOS API")

# CORS for Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In prod, set to frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- STARTUP DIAGNOSTICS ---
import groq
DIAGNOSTICS = {"status": "pending"}

try:
    print("[DIAG] DIAGNOSTICS: Starting...")
    key = os.getenv("GROQ_API_KEY")
    if not key:
        print("[WARN] DIAGNOSTICS: GROQ_API_KEY NOT FOUND in Environment")
        DIAGNOSTICS["key_found"] = False
    else:
        print(f"[OK] DIAGNOSTICS: Key found ({key[:5]}...)")
        DIAGNOSTICS["key_found"] = True
        
        # Test Connection
        try:
            test_client = groq.Groq(api_key=key)
            test_resp = test_client.chat.completions.create(
                messages=[{"role": "user", "content": "ping"}],
                model="llama-3.1-8b-instant"
            )
            print(f"[OK] DIAGNOSTICS: Groq Ping Success: {test_resp.choices[0].message.content}")
            DIAGNOSTICS["connection"] = "success"
        except Exception as e:
            print(f"[ERR] DIAGNOSTICS: Groq Connection FAILED: {e}")
            DIAGNOSTICS["connection"] = f"failed: {str(e)}"
except Exception as e:
    print(f"[ERR] DIAGNOSTICS: Critical Setup Error: {e}")

# Initialize Agent (Singleton for MVP)
# In production, we might want per-session agents or lazy loading
# Initialize Agent (Singleton for MVP)
# In production, we might want per-session agents or lazy loading
# Lazy Loading Global State
GDPR_INDEXER = None

def get_gdpr_indexer():
    global GDPR_INDEXER
    if GDPR_INDEXER is None:
        try:
            print("[...] Lazy Loading FAISS Indexer...")
            if os.path.exists("data/processed/gdpr_structured.json"):
                indexer = ClauseIndexer()
                # Load and Build
                with open("data/processed/gdpr_structured.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                    texts = []
                    metadata = []
                    if "articles" in data:
                        for art in data["articles"]:
                            for clause in art.get("clauses", []):
                                texts.append(clause["text"])
                                metadata.append({
                                    "article_id": art["article_id"],
                                    "clause_id": clause["clause_id"],
                                    "text": clause["text"]
                                })
                    
                    if texts:
                        print(f"[OK] Building Index with {len(texts)} clauses...")
                        indexer.build(texts, metadata)
                        GDPR_INDEXER = indexer
                    else:
                        print("[WARN] No texts found in GDPR data!")
            else:
                print("[WARN] GDPR Data file not found.")
        except Exception as e:
            print(f"[WARN] Indexer Initialization Failed: {e}")
    return GDPR_INDEXER

class ChatRequest(BaseModel):
    query: str
    domain: str = "GDPR"
    model_tier: str = "Tier 1"
    thread_id: str = "default"

@app.get("/")
def health_check():
    return {"status": "active", "system": "ComplianceOS", "diagnostics": DIAGNOSTICS}

@app.post("/chat")
@app.post("/api/chat")
@app.post("/api/analyze")
async def chat_endpoint(req: ChatRequest):
    """
    Standard Request-Response using LangGraph agent pipeline.
    """
    try:
        from agent.graph import run_graph

        result = run_graph(
            user_query=req.query,
            domain=req.domain,
            thread_id=req.thread_id,
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat/stream")
@app.post("/api/chat/stream")
async def stream_chat_endpoint(req: ChatRequest):
    """
    SSE Streaming Endpoint — Streams real LangGraph node transitions.
    Each node fires an SSE event as it completes. Langfuse traces
    are piped silently in the background when configured.
    """
    from agent.graph import stream_graph

    async def event_generator():
        async for chunk in stream_graph(
            user_query=req.query,
            domain=req.domain,
            thread_id=req.thread_id,
        ):
            yield {
                "event": "message",
                "data": chunk,
            }

    return EventSourceResponse(event_generator())


class FollowupRequest(BaseModel):
    query: str
    domain: str = "GDPR"
    thread_id: str = "default"
    selected_options: list[str] = []
    custom_text: str = ""


@app.post("/chat/followup")
@app.post("/api/chat/followup")
async def followup_endpoint(req: FollowupRequest):
    """
    SSE Streaming Endpoint for follow-up after clarification.
    Re-runs the graph with user's selected clarification answers.
    """
    from agent.graph import stream_graph

    # Build the user_selections list from selected options + custom text
    user_selections = list(req.selected_options)
    if req.custom_text.strip():
        user_selections.append(f"Additional context: {req.custom_text.strip()}")

    async def event_generator():
        async for chunk in stream_graph(
            user_query=req.query,
            domain=req.domain,
            thread_id=req.thread_id,
            user_selections=user_selections,
        ):
            yield {
                "event": "message",
                "data": chunk,
            }

    return EventSourceResponse(event_generator())

