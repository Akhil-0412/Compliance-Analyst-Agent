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
            print("⏳ Lazy Loading FAISS Indexer...")
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
                        print(f"🚀 Building Index with {len(texts)} clauses...")
                        indexer.build(texts, metadata)
                        GDPR_INDEXER = indexer
                    else:
                        print("⚠️ No texts found in GDPR data!")
            else:
                print("⚠️ GDPR Data file not found.")
        except Exception as e:
            print(f"⚠️ Indexer Initialization Failed: {e}")
    return GDPR_INDEXER

class ChatRequest(BaseModel):
    query: str
    domain: str = "GDPR"
    model_tier: str = "Tier 1"

@app.get("/")
def health_check():
    return {"status": "active", "system": "ComplianceOS"}

@app.post("/chat")
@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    """
    Standard Request-Response (Non-streaming)
    """
    try:
        # Lazy load indexer on first request
        indexer = get_gdpr_indexer()
        
        agent = ComplianceAgent(
            indexer=indexer, 
            data_path="data/processed/gdpr_structured.json", 
            domain=req.domain
        )
        response = agent.analyze(req.query)
        
        # Output is likely a Pydantic object (ComplianceResponse)
        if hasattr(response, 'model_dump'):
            return response.model_dump()
        return {"response": response} # Fallback for string
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chat/stream")
async def stream_chat_endpoint(query: str, domain: str = "GDPR"):
    """
    Streaming Endpoint for 'Live Processing' visualization.
    We need to refactor the Agent to yield steps.
    For now, we simulate steps + return final result.
    """
    async def event_generator():
        # 1. Yield Search Status
        yield {
            "event": "status",
            "data": json.dumps({"step": "searching", "message": f"Scanning {domain} regulations..."})
        }
        await asyncio.sleep(1) # Simulation for UI effect
        
        # 2. Yield Reading Status
        yield {
            "event": "status", 
            "data": json.dumps({"step": "reading", "message": "Analyzing legal context..."})
        }
        await asyncio.sleep(1) # Simulation
        
        # 3. Perform Actual Work
        try:
            agent = ComplianceAgent(
                indexer=GDPR_INDEXER, 
                data_path="data/processed/gdpr_structured.json", 
                domain=domain
            )
            response = agent.analyze(query)
            
            # Serialize
            final_data = {}
            if hasattr(response, 'model_dump'):
                final_data = response.model_dump()
            else:
                final_data = {"summary": str(response)}

            yield {
                "event": "result",
                "data": json.dumps(final_data)
            }
            
        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)})
            }

    return EventSourceResponse(event_generator())
