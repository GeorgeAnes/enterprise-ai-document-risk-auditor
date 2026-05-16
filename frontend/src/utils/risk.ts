import type { ClaimAudit, SupportLabel } from "../types";

export function labelTone(label: SupportLabel): string {
  switch (label) {
    case "Supported":
      return "supported";
    case "Weakly supported":
      return "weak";
    case "Unsupported":
      return "danger";
    case "Vague / non-verifiable":
      return "vague";
    case "Needs human review":
      return "review";
    default:
      return "neutral";
  }
}

export function riskSeverity(score: number): string {
  if (score >= 75) return "Critical";
  if (score >= 55) return "High";
  if (score >= 30) return "Elevated";
  return "Nominal";
}

export function buildDocumentContext(documentText: string, claim: ClaimAudit | null): string {
  if (!documentText.trim()) {
    return "No source document text is available in the current session.";
  }
  if (!claim) {
    return documentText.slice(0, 900);
  }

  const lowerDocument = documentText.toLowerCase();
  const claimStart = claim.text.slice(0, 80).toLowerCase();
  const index = lowerDocument.indexOf(claimStart);
  if (index === -1) {
    return documentText.slice(0, 1100);
  }

  const start = Math.max(0, index - 420);
  const end = Math.min(documentText.length, index + claim.text.length + 520);
  return `${start > 0 ? "... " : ""}${documentText.slice(start, end)}${end < documentText.length ? " ..." : ""}`;
}
