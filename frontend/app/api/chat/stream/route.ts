/**
 * Next.js API Route – SSE proxy for the Python backend.
 * Browser fetches same-origin /api/chat/stream (no CORS),
 * this handler forwards to the Python backend and pipes the stream back.
 */
export const runtime = "nodejs";       // use Node runtime, not Edge
export const dynamic = "force-dynamic"; // never cache

const BACKEND = process.env.BACKEND_URL || "http://127.0.0.1:8085";

export async function POST(req: Request) {
    const body = await req.json();

    const upstream = await fetch(`${BACKEND}/api/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });

    if (!upstream.ok) {
        return new Response(`Backend error: ${upstream.status}`, { status: upstream.status });
    }

    // Pipe the SSE stream straight through
    return new Response(upstream.body, {
        status: 200,
        headers: {
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
        },
    });
}
