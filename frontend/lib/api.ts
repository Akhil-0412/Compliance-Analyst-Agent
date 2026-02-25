import { ComplianceResponse } from "@/types/api";

export const API_URL = process.env.NEXT_PUBLIC_API_URL || '/api';

export async function analyzeQuery(query: string): Promise<ComplianceResponse> {
    try {
        console.log("SENDING REQUEST TO:", `${API_URL}/analyze`);
        console.log("PAYLOAD:", JSON.stringify({ query }));

        const res = await fetch(`${API_URL}/analyze`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ query }),
        });

        if (!res.ok) {
            const errorData = await res.json().catch(() => ({}));
            throw new Error(errorData.detail || "Analysis request failed");
        }

        const data = await res.json();

        // Map python's 'gdpr_subsection' back to 'article' and 'regulation' for the frontend TS types.
        if (data.reasoning_map && Array.isArray(data.reasoning_map)) {
            data.reasoning_map = data.reasoning_map.map((node: any) => ({
                ...node,
                regulation: node.regulation || "GDPR",
                article: node.article || node.gdpr_subsection || "General"
            }));
        }

        // Re-construct the expected Analysis and Decision wrapper
        let decision: ComplianceResponse["decision"] = "REVIEW_REQUIRED";
        if (data.needs_clarification) decision = "CLARIFICATION_REQUIRED";
        else if (data.risk_level === "High") decision = "BLOCKED";
        else if (data.risk_level === "Low") decision = "AUTO_APPROVED";

        return {
            decision,
            analysis: data
        } as ComplianceResponse;
    } catch (error) {
        console.error("API Error:", error);
        throw error;
    }
}


// --- SSE Node Transition Event ---
export interface NodeEvent {
    event: "node";
    node: string;
    label: string;
    retry_count: number;
}

// --- SSE Streaming Consumer ---
export async function analyzeQueryStream(
    query: string,
    onNodeUpdate: (event: NodeEvent) => void,
    domain: string = "GDPR",
    threadId: string = "default"
): Promise<ComplianceResponse> {
    const res = await fetch(`${API_URL}/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, domain, thread_id: threadId }),
    });

    if (!res.ok) {
        throw new Error(`Stream request failed: ${res.status}`);
    }

    const reader = res.body?.getReader();
    if (!reader) throw new Error("No readable stream");

    const decoder = new TextDecoder();
    let buffer = "";
    let finalData: any = null;

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Normalize line endings (proxy may send \r\n)
        buffer = buffer.replace(/\r\n/g, "\n");

        // SSE events are separated by double newlines
        const events = buffer.split("\n\n");
        buffer = events.pop() || "";

        for (const eventBlock of events) {
            const lines = eventBlock.split("\n");
            let dataLine = "";

            for (const line of lines) {
                if (line.startsWith("data:")) {
                    dataLine = line.slice(5).trim();
                }
            }

            if (!dataLine || dataLine === "[DONE]") continue;

            try {
                const parsed = JSON.parse(dataLine);

                if (parsed.event === "node") {
                    onNodeUpdate(parsed as NodeEvent);
                } else if (parsed.event === "result") {
                    finalData = parsed.data;
                } else if (parsed.event === "error") {
                    throw new Error(parsed.data?.message || "Stream error");
                }
            } catch (e) {
                if (e instanceof SyntaxError) continue; // Skip malformed JSON
                throw e;
            }
        }
    }

    if (!finalData) {
        throw new Error("Stream ended without result");
    }

    // Handle clarification response (type: "clarification")
    if (finalData.type === "clarification") {
        return {
            decision: "CLARIFICATION_REQUIRED",
            analysis: {
                needs_clarification: true,
                missing_preconditions: [],
                clarification_options: finalData.options || [],
                reasoning_map: [],
                risk_level: "Unknown",
                confidence: 0,
                summary: finalData.summary || "Additional context is needed.",
            },
            clarification: finalData,
        } as ComplianceResponse;
    }

    // Transform to ComplianceResponse (same logic as analyzeQuery)
    const data = finalData;

    // Normalize risk_level: backend sends lowercase ("low"), frontend expects Title Case ("Low")
    if (data.risk_level && typeof data.risk_level === "string") {
        data.risk_level = data.risk_level.charAt(0).toUpperCase() + data.risk_level.slice(1).toLowerCase();
    }

    if (data.reasoning_map && Array.isArray(data.reasoning_map)) {
        data.reasoning_map = data.reasoning_map.map((node: any) => ({
            ...node,
            regulation: node.regulation || "GDPR",
            article: node.article || node.gdpr_subsection || "General"
        }));
    } else {
        data.reasoning_map = [];
    }

    data.missing_preconditions = data.missing_preconditions || [];

    let decision: ComplianceResponse["decision"] = "REVIEW_REQUIRED";
    if (data.needs_clarification) decision = "CLARIFICATION_REQUIRED";
    else if (data.risk_level === "High") decision = "BLOCKED";
    else if (data.risk_level === "Low") decision = "AUTO_APPROVED";

    return { decision, analysis: data } as ComplianceResponse;
}


// --- Submit Followup (after clarification) ---
export async function submitFollowup(
    query: string,
    selectedOptions: string[],
    customText: string,
    onNodeUpdate: (event: NodeEvent) => void,
    domain: string = "GDPR",
    threadId: string = "default"
): Promise<ComplianceResponse> {
    const res = await fetch(`${API_URL}/chat/followup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            query,
            domain,
            thread_id: threadId,
            selected_options: selectedOptions,
            custom_text: customText,
        }),
    });

    if (!res.ok) {
        throw new Error(`Followup request failed: ${res.status}`);
    }

    const reader = res.body?.getReader();
    if (!reader) throw new Error("No readable stream");

    const decoder = new TextDecoder();
    let buffer = "";
    let finalData: any = null;

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        buffer = buffer.replace(/\r\n/g, "\n");

        const events = buffer.split("\n\n");
        buffer = events.pop() || "";

        for (const eventBlock of events) {
            const lines = eventBlock.split("\n");
            let dataLine = "";

            for (const line of lines) {
                if (line.startsWith("data:")) {
                    dataLine = line.slice(5).trim();
                }
            }

            if (!dataLine || dataLine === "[DONE]") continue;

            try {
                const parsed = JSON.parse(dataLine);

                if (parsed.event === "node") {
                    onNodeUpdate(parsed as NodeEvent);
                } else if (parsed.event === "result") {
                    finalData = parsed.data;
                } else if (parsed.event === "error") {
                    throw new Error(parsed.data?.message || "Stream error");
                }
            } catch (e) {
                if (e instanceof SyntaxError) continue;
                throw e;
            }
        }
    }

    if (!finalData) {
        throw new Error("Followup stream ended without result");
    }

    const data = finalData;

    if (data.risk_level && typeof data.risk_level === "string") {
        data.risk_level = data.risk_level.charAt(0).toUpperCase() + data.risk_level.slice(1).toLowerCase();
    }

    if (data.reasoning_map && Array.isArray(data.reasoning_map)) {
        data.reasoning_map = data.reasoning_map.map((node: any) => ({
            ...node,
            regulation: node.regulation || "GDPR",
            article: node.article || node.gdpr_subsection || "General"
        }));
    } else {
        data.reasoning_map = [];
    }

    data.missing_preconditions = data.missing_preconditions || [];

    let decision: ComplianceResponse["decision"] = "REVIEW_REQUIRED";
    if (data.needs_clarification) decision = "CLARIFICATION_REQUIRED";
    else if (data.risk_level === "High") decision = "BLOCKED";
    else if (data.risk_level === "Low") decision = "AUTO_APPROVED";

    return { decision, analysis: data } as ComplianceResponse;
}
