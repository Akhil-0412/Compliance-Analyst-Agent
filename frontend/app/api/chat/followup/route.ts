/**
 * Next.js API Route – SSE proxy for the followup endpoint.
 * Forwards clarification follow-up requests to the Python backend.
 */
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const BACKEND = process.env.BACKEND_URL || "http://127.0.0.1:8085";

export async function POST(req: Request) {
    const body = await req.json();

    const upstream = await fetch(`${BACKEND}/api/chat/followup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });

    if (!upstream.ok) {
        return new Response(`Backend error: ${upstream.status}`, { status: upstream.status });
    }

    return new Response(upstream.body, {
        status: 200,
        headers: {
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
        },
    });
}
