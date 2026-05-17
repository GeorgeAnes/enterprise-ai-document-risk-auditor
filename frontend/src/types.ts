export type SupportLabel =
  | "Supported"
  | "Weakly supported"
  | "Unsupported"
  | "Vague / non-verifiable"
  | "Needs human review";

export interface SampleInfo {
  id: string;
  title: string;
  description: string;
  filename: string;
}

export interface SampleDocument extends SampleInfo {
  content: string;
}

export interface EvidenceSnippet {
  chunk_id: string;
  text: string;
  source: string;
  score: number;
  heading?: string | null;
}

export interface ClaimAudit {
  id: string;
  text: string;
  source_chunk_id: string;
  label: SupportLabel;
  risk_score: number;
  confidence: number;
  explanation: string;
  factors: string[];
  evidence: EvidenceSnippet[];
  llm_review?: ClaimLLMReview | null;
}

export interface ClaimLLMReview {
  claim_id: string;
  reviewer_status: "completed" | "fallback_text" | "unavailable" | "disabled";
  reviewer_note?: string | null;
  suggested_rewrite?: string | null;
  missing_evidence_questions: string[];
  business_impact?: string | null;
  human_review_priority: "Low" | "Medium" | "High" | "Critical";
  confidence: number;
}

export interface AuditSummary {
  title: string;
  total_claims: number;
  overall_risk_score: number;
  label_counts: Record<string, number>;
  executive_summary: string;
  review_checklist: string[];
}

export interface LLMReview {
  enabled: boolean;
  provider: string;
  model?: string | null;
  status: "disabled" | "not_configured" | "completed" | "error" | "unavailable";
  summary?: string | null;
  reviewer_notes: string[];
  raw_text?: string | null;
  error?: string | null;
}

export interface AuditResponse {
  document_title: string;
  summary: AuditSummary;
  claims: ClaimAudit[];
  markdown_report: string;
  llm_review?: LLMReview | null;
}

export type LabelFilter = SupportLabel | "All";
