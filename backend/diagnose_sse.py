"""
SSE Diagnostic Script - Tests every layer in isolation.
Run: python diagnose_sse.py
"""
import sys, os, time, asyncio, traceback

sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv()

PASS = "[PASS]"
FAIL = "[FAIL]"
results = []

def log(label, ok, detail=""):
    tag = PASS if ok else FAIL
    msg = f"{tag} {label}: {detail}"
    print(msg)
    results.append((label, ok, detail))

# ---- TEST 1: API Key ----
key = os.getenv("GROQ_API_KEY")
log("GROQ_API_KEY loaded", bool(key), f"{key[:8]}..." if key else "NOT SET")

# ---- TEST 2: LLM Client init ----
try:
    from agent.llm_client import get_llm_client
    base, instructor_client, models, provider = get_llm_client()
    log("LLM Client init", True, f"provider={provider}, models={models}")
except Exception as e:
    log("LLM Client init", False, str(e))

# ---- TEST 3: Quick LLM call ----
try:
    from groq import Groq
    c = Groq(api_key=key)
    r = c.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":"say ok"}], temperature=0)
    log("LLM API call", True, r.choices[0].message.content[:50])
except Exception as e:
    log("LLM API call", False, str(e)[:100])

# ---- TEST 4: Graph compilation ----
try:
    from agent.graph import compile_graph
    g = compile_graph()
    log("Graph compiles (no checkpointer)", True, str(type(g)))
except Exception as e:
    log("Graph compiles", False, traceback.format_exc()[-200:])

# ---- TEST 5: Graph with AsyncSqliteSaver ----
async def test_async_checkpointer():
    try:
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
        async with AsyncSqliteSaver.from_conn_string("checkpoints.db") as ckpt:
            g = compile_graph(checkpointer=ckpt)
            log("Graph compiles (async checkpointer)", True, str(type(g)))
    except Exception as e:
        log("Graph compiles (async checkpointer)", False, traceback.format_exc()[-200:])

asyncio.run(test_async_checkpointer())

# ---- TEST 6: stream_graph yields events ----
async def test_stream():
    try:
        from agent.graph import stream_graph
        events = []
        start = time.time()
        async for chunk in stream_graph("is email a personal data", "GDPR", "diag_thread"):
            elapsed = round(time.time() - start, 1)
            safe = chunk[:100].encode('ascii', 'replace').decode()
            events.append(safe)
            print(f"  [{elapsed}s] EVENT: {safe}")
            if time.time() - start > 90:
                print("  TIMEOUT after 90s")
                break
        has_result = any('"event": "result"' in e for e in events)
        has_done = any("[DONE]" in e for e in events)
        log("stream_graph yields events", len(events) > 0, f"{len(events)} events, has_result={has_result}, has_done={has_done}")
    except Exception as e:
        log("stream_graph yields events", False, traceback.format_exc()[-300:])

asyncio.run(test_stream())

# ---- TEST 7: HTTP endpoint test ----
try:
    import requests
    start = time.time()
    r = requests.post(
        "http://127.0.0.1:8085/api/chat/stream",
        json={"query": "is email personal data", "domain": "GDPR", "thread_id": "diag_http"},
        stream=True, timeout=90,
    )
    log("HTTP POST /api/chat/stream status", r.status_code == 200, f"status={r.status_code}")
    http_events = []
    for line in r.iter_lines():
        safe = line[:120].decode('utf-8', errors='replace') if isinstance(line, bytes) else str(line)[:120]
        http_events.append(safe)
        print(f"  HTTP: {safe}")
        if len(http_events) > 30: break
    log("HTTP SSE events received", len(http_events) > 0, f"{len(http_events)} lines")
except Exception as e:
    log("HTTP endpoint", False, str(e)[:200])

# ---- SUMMARY ----
print("\n" + "="*60)
print("DIAGNOSTIC SUMMARY")
print("="*60)
for label, ok, detail in results:
    tag = PASS if ok else FAIL
    print(f"  {tag} {label}")
    if not ok:
        print(f"       -> {detail[:100]}")

failures = [r for r in results if not r[1]]
if failures:
    print(f"\n{len(failures)} FAILURE(S) found. Fix the first failure and re-run.")
else:
    print("\nAll tests passed! The bug is in the frontend or Next.js proxy layer.")
