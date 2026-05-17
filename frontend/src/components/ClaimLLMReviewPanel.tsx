import { BrainCircuit } from "lucide-react";
import type { ClaimLLMReview } from "../types";

interface ClaimLLMReviewPanelProps {
  review?: ClaimLLMReview | null;
}

function ClaimLLMReviewPanel({ review }: ClaimLLMReviewPanelProps) {
  if (!review) {
    return (
      <section className="glass-panel claim-llm-panel unavailable">
        <div className="panel-title compact">
          <BrainCircuit size={18} />
          <div>
            <p className="eyebrow">Local Gemma reviewer</p>
            <h2>Reviewer layer unavailable</h2>
          </div>
        </div>
        <p>Local reviewer unavailable. Deterministic audit remains available.</p>
      </section>
    );
  }

  return (
    <section className={`glass-panel claim-llm-panel ${review.reviewer_status}`}>
      <div className="panel-title compact">
        <BrainCircuit size={18} />
        <div>
          <p className="eyebrow">Local Gemma reviewer</p>
          <h2>{review.reviewer_status === "completed" ? "Structured reviewer note" : "Fallback reviewer note"}</h2>
        </div>
      </div>
      {review.reviewer_note && <p>{review.reviewer_note}</p>}
      <div className="reviewer-detail-grid">
        <article>
          <span>Human review priority</span>
          <strong>{review.human_review_priority}</strong>
        </article>
        <article>
          <span>Reviewer confidence</span>
          <strong>{Math.round(review.confidence * 100)}%</strong>
        </article>
      </div>
      {review.suggested_rewrite && (
        <div className="review-block">
          <h3>Suggested safer rewrite</h3>
          <p>{review.suggested_rewrite}</p>
        </div>
      )}
      {review.business_impact && (
        <div className="review-block">
          <h3>Business impact</h3>
          <p>{review.business_impact}</p>
        </div>
      )}
      {review.missing_evidence_questions.length > 0 && (
        <div className="review-block">
          <h3>Missing evidence questions</h3>
          <ul>
            {review.missing_evidence_questions.map((question) => (
              <li key={question}>{question}</li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

export default ClaimLLMReviewPanel;
