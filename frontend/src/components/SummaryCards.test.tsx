import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import SummaryCards from "./SummaryCards";

describe("SummaryCards", () => {
  it("renders audit metrics", () => {
    render(
      <SummaryCards
        summary={{
          title: "Demo",
          total_claims: 4,
          overall_risk_score: 52,
          label_counts: {
            Supported: 1,
            Unsupported: 2,
            "Needs human review": 1
          },
          executive_summary: "Demo summary",
          review_checklist: []
        }}
      />
    );

    expect(screen.getByText("Overall risk")).toBeTruthy();
    expect(screen.getByText("52/100")).toBeTruthy();
    expect(screen.getByText("Claims extracted")).toBeTruthy();
  });
});
