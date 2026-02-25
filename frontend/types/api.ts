export interface ReasoningNode {
    fact: string;
    legal_meaning: string;
    regulation: "GDPR" | "CCPA" | "FDA" | "IRS" | "Other";
    article: string;
    justification: string;
    regulation_version?: string | null;
    effective_date?: string | null;
}

export interface ClarificationOption {
    id: string;
    text: string;
    rank: number;
}

export interface AnalysisOutput {
    needs_clarification: boolean;
    missing_preconditions: string[];
    clarification_options?: ClarificationOption[];
    reasoning_map: ReasoningNode[];
    risk_level: "Low" | "Medium" | "High" | "Unknown";
    confidence: number;
    summary: string;
}

export interface ClarificationData {
    type: "clarification";
    summary: string;
    options: ClarificationOption[];
}

export interface ComplianceResponse {
    analysis: AnalysisOutput;
    decision: "AUTO_APPROVED" | "REVIEW_REQUIRED" | "BLOCKED" | "CLARIFICATION_REQUIRED";
    clarification?: ClarificationData;
}
