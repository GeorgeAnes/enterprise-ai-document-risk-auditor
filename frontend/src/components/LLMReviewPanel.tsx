import { Sparkles } from "lucide-react";
import type { ClaimAudit, LLMReview } from "../types";

interface LLMReviewPanelProps {
  review?: LLMReview | null;
  claims?: ClaimAudit[];
}

function LLMReviewPanel({ review, claims = [] }: LLMReviewPanelProps) {
  const reviewedClaims = claims.filter((claim) => claim.llm_review);
  const status = review?.status ?? "disabled";
  const completed = status === "completed";
  const unavailable = status === "error" || status === "unavailable" || status === "not_configured";

  const title = completed ? "Gemma reviewer completed" : unavailable ? "Local reviewer unavailable" : "Local reviewer disabled";
  const detail = completed
    ? review?.summary || "Local reviewer added structured notes for high-risk claims."
    : unavailable
      ? "Local reviewer unavailable. Deterministic audit remains available."
      : "Deterministic audit completed. Enable LM Studio/Gemma for interpretive reviewer notes.";

  return (
    <section className={`llm-panel ${status}`}>
      <div className="section-title">
        <Sparkles size={17} />
        <span>{title}</span>
      </div>
      <p className="llm-meta">
        Deterministic audit completed
        {review?.model ? ` / ${review.model}` : ""}
      </p>
      {detail && <p>{detail}</p>}
      <div className="reviewer-meter">
        <span>Claims reviewed locally</span>
        <strong>{reviewedClaims.length}</strong>
      </div>
      {completed && review?.reviewer_notes && review.reviewer_notes.length > 0 && (
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
