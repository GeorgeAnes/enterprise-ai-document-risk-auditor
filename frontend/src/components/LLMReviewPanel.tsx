import { Sparkles } from "lucide-react";
import type { LLMReview } from "../types";

interface LLMReviewPanelProps {
  review?: LLMReview | null;
}

function LLMReviewPanel({ review }: LLMReviewPanelProps) {
  if (!review || review.status === "disabled") {
    return null;
  }

  const providerLabel = review.provider === "openai_compatible" ? "OpenAI-compatible reviewer" : "Gemini reviewer";
  const title = review.status === "completed" ? providerLabel : `${providerLabel} setup`;
  const detail =
    review.status === "not_configured"
      ? setupMessage(review.provider)
      : review.status === "error"
        ? review.error || "The optional LLM reviewer returned an error. The deterministic audit still completed."
        : review.summary;

  return (
    <section className={`llm-panel ${review.status}`}>
      <div className="section-title">
        <Sparkles size={17} />
        <span>{title}</span>
      </div>
      <p className="llm-meta">
        {review.provider}
        {review.model ? ` / ${review.model}` : ""}
      </p>
      {detail && <p>{detail}</p>}
      {review.status === "completed" && review.reviewer_notes.length > 0 && (
        <ul>
          {review.reviewer_notes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      )}
    </section>
  );
}

function setupMessage(provider: string): string {
  if (provider === "openai_compatible") {
    return "Set LLM_MODE=openai_compatible and configure OPENAI_BASE_URL, OPENAI_API_KEY, and OPENAI_MODEL in your local .env file, then restart the backend.";
  }
  return "Set LLM_MODE=gemini and replace GEMINI_API_KEY in your local .env file, then restart the backend.";
}

export default LLMReviewPanel;
