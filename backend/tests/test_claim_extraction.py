from backend.app.core.chunk import chunk_text
from backend.app.core.claim_extraction import extract_claims


def test_extracts_specific_and_vague_claims():
    text = """
    Executive Summary
    The new workflow reduces manual review time by 35 percent in the pilot team.
    The platform is best-in-class and seamless for all departments.
    """
    chunks = chunk_text(text)
    claims = extract_claims(chunks)

    assert len(claims) >= 2
    assert any("35 percent" in claim.text for claim in claims)
    assert any("best-in-class" in claim.text for claim in claims)
