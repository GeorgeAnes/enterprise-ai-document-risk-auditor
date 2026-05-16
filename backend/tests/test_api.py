from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_audit_endpoint_with_text():
    payload = {
        "filename": "demo.md",
        "text": (
            "The analytics program reduced rework by 25 percent in Q1 2026. "
            "The pilot evidence states that rework decreased from 120 cases to 90 cases in Q1 2026. "
            "The model is guaranteed to be fully compliant in all cases."
        ),
    }
    response = client.post("/audit", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["total_claims"] >= 2
    assert data["claims"]
    assert "markdown_report" in data
