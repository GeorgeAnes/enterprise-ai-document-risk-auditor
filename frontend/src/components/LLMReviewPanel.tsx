import { Sparkles } from "lucide-react";
import type { LLMReview } from "../types";

interface LLMReviewPanelProps {
  review?: LLMReview | null;
}

function LLMReviewPanel({ review }: LLMReviewPanelProps) {
  if (!review || review.status === "disabled") {
    return null;
  }

  const title = review.status === "completed" ? "Gemini reviewer" : "Gemini reviewer setup";
  const detail =
    review.status === "not_configured"
      ? "Set LLM_MODE=gemini and replace GEMINI_API_KEY in your local .env file, then restart the backend."
      : review.status === "error"
        ? review.error || "Gemini returned an error. The deterministic audit still completed."
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

export default LLMReviewPanel;
