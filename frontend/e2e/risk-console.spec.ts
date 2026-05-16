import { expect, test } from "@playwright/test";

test("sample document audit moves from scan to overview to finding deep dive", async ({ page }) => {
  await page.route("http://127.0.0.1:8010/samples", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: "consulting_report",
          title: "Consulting Report Sample",
          description: "Synthetic operating model report with mixed support quality.",
          filename: "consulting_report_sample.md"
        }
      ])
    });
  });

  await page.route("http://127.0.0.1:8010/samples/consulting_report", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        id: "consulting_report",
        title: "Consulting Report Sample",
        description: "Synthetic operating model report with mixed support quality.",
        filename: "consulting_report_sample.md",
        content:
          "The operating model is guaranteed to eliminate manual rework. Pilot evidence showed exceptions remained in two teams."
      })
    });
  });

  await page.route("http://127.0.0.1:8010/audit", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        document_title: "Consulting Report Sample",
        summary: {
          title: "Consulting Report Sample",
          total_claims: 2,
          overall_risk_score: 74,
          label_counts: {
            Supported: 0,
            "Weakly supported": 1,
            Unsupported: 0,
            "Vague / non-verifiable": 0,
            "Needs human review": 1
          },
          executive_summary: "One high-risk claim needs evidence and human review.",
          review_checklist: [
            "Confirm that every high-risk claim has a traceable source passage.",
            "Replace guaranteed language with scoped evidence."
          ]
        },
        claims: [
          {
            id: "C001",
            text: "The operating model is guaranteed to eliminate manual rework.",
            source_chunk_id: "D001",
            label: "Needs human review",
            risk_score: 90,
            confidence: 0.81,
            explanation: "The claim uses absolute language and has weak document grounding.",
            factors: ["Strong certainty language", "Low support evidence"],
            evidence: [
              {
                chunk_id: "E001",
                text: "Pilot evidence showed exceptions remained in two teams.",
                source: "document",
                score: 0.34,
                heading: "Pilot evidence"
              }
            ]
          },
          {
            id: "C002",
            text: "Pilot evidence showed exceptions remained in two teams.",
            source_chunk_id: "D002",
            label: "Weakly supported",
            risk_score: 42,
            confidence: 0.74,
            explanation: "The statement has partial support in the document.",
            factors: ["Partial evidence match"],
            evidence: [
              {
                chunk_id: "E002",
                text: "Pilot evidence showed exceptions remained in two teams.",
                source: "document",
                score: 0.72,
                heading: "Pilot evidence"
              }
            ]
          }
        ],
        markdown_report: "# Consulting Report Sample\n\nOne high-risk claim needs evidence and human review.",
        llm_review: {
          enabled: false,
          provider: "none",
          status: "disabled",
          reviewer_notes: []
        }
      })
    });
  });

  await page.goto("/scan");

  await expect(page.getByRole("heading", { name: "Load a controlled document" })).toBeVisible();
  const scanButton = page.getByRole("button", { name: /Run risk scan/i });
  await expect(scanButton).toBeEnabled();
  await scanButton.click();

  await page.waitForURL("**/overview");
  await expect(page.getByText("Risk posture", { exact: true })).toBeVisible();
  await expect(page.getByText("Support distribution")).toBeVisible();
  await expect(page.getByText("Top risks")).toBeVisible();
  await expect(page.getByRole("button", { name: /Markdown report/i })).toBeVisible();

  await page.locator(".risk-card").first().click();
  await expect(page).toHaveURL(/\/findings\//);
  await expect(page.getByText("Why this claim is flagged")).toBeVisible();
  await expect(page.getByText("Grounding snippets")).toBeVisible();
  await expect(page.getByText("Document context")).toBeVisible();
});
