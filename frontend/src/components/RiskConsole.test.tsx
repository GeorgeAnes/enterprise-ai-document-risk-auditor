import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
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
});
