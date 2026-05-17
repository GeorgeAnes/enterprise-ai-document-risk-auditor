import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ClaimLLMReviewPanel from "./ClaimLLMReviewPanel";
import ClaimCategoryMatrix from "./ClaimCategoryMatrix";
import RiskScoreRing from "./RiskScoreRing";

describe("risk console components", () => {
  it("renders risk score and claim categories", () => {
    render(
      <>
        <RiskScoreRing score={68} band="High" />
        <ClaimCategoryMatrix
          total={4}
          rows={[
            { label: "Supported", count: 1, tone: "supported" },
            { label: "Weakly supported", count: 1, tone: "weak" },
            { label: "Unsupported", count: 2, tone: "danger" }
          ]}
        />
      </>
    );

    expect(screen.getByText("Risk posture")).toBeTruthy();
    expect(screen.getByText("68")).toBeTruthy();
    expect(screen.getByText("Support distribution")).toBeTruthy();
    expect(screen.getByText("Unsupported")).toBeTruthy();
  });

  it("renders claim reviewer output and deterministic fallback state", () => {
    const { rerender } = render(
      <ClaimLLMReviewPanel
        review={{
          claim_id: "C001",
          reviewer_status: "completed",
          reviewer_note: "The claim needs clearer evidence.",
          suggested_rewrite: "The pilot suggests a possible reduction in the tested scope.",
          missing_evidence_questions: ["Which source validates the metric?"],
          business_impact: "The claim could affect rollout decisions.",
          human_review_priority: "High",
          confidence: 0.8
        }}
      />
    );

    expect(screen.getByText("Local Gemma reviewer")).toBeTruthy();
    expect(screen.getByText("Suggested safer rewrite")).toBeTruthy();
    expect(screen.getByText("Which source validates the metric?")).toBeTruthy();

    rerender(<ClaimLLMReviewPanel review={null} />);
    expect(screen.getByText("Local reviewer unavailable. Deterministic audit remains available.")).toBeTruthy();
  });
});
