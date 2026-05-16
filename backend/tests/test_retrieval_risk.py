from backend.app.core.chunk import chunk_text
from backend.app.core.claim_extraction import extract_claims
from backend.app.core.retrieval import retrieve_evidence
from backend.app.core.risk_scoring import score_claims


def test_retrieval_and_risk_scoring_flags_unsupported_claims():
    document = """
    The rollout reduced invoice cycle time by 42 percent in April 2026.
    Pilot logs show invoice cycle time moved from 10 days to 6 days in April 2026.
    The platform is guaranteed to remove all operational risk.
    """
    chunks = chunk_text(document)
    claims = extract_claims(chunks)
    evidence = retrieve_evidence(claims, chunks)
    audits = score_claims(claims, evidence)

    assert audits
    assert any(audit.label in {"Unsupported", "Needs human review"} for audit in audits)
    assert all(0 <= audit.risk_score <= 100 for audit in audits)
