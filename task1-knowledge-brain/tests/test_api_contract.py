import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from app.config import settings
from app.main import app
from app.storage import create_escalation, resolve_escalation, list_approved_knowledge


def test_health_endpoint():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_escalation_can_be_created_and_retrieved(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "ESCALATION_DB_PATH", str(tmp_path / "escalations.sqlite3"))
    client = TestClient(app)

    created = client.post("/escalations", json={
        "question": "Can you confirm this account-specific refund?",
        "reason": "The knowledge base does not contain account billing records.",
        "evidence": [],
    })
    assert created.status_code == 201
    escalation = created.json()
    assert escalation["status"] == "open"

    fetched = client.get(f"/escalations/{escalation['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["question"] == "Can you confirm this account-specific refund?"

    listing = client.get("/escalations?status=open")
    assert listing.status_code == 200
    assert any(item["id"] == escalation["id"] for item in listing.json()["items"])


def test_human_resolution_creates_versioned_knowledge_record(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "ESCALATION_DB_PATH", str(tmp_path / "knowledge.sqlite3"))
    escalation = create_escalation("How do I do a rare configuration?", "Insufficient evidence")
    resolved = resolve_escalation(
        escalation["id"],
        "The reviewed answer is to open the approved settings page.",
        ["https://example.test/approved-article"],
    )
    assert resolved is not None
    assert resolved["status"] == "resolved"
    knowledge = list_approved_knowledge()
    record = next(item for item in knowledge if item["escalation_id"] == escalation["id"])
    assert record["version"] == 1
    assert "approved settings page" in record["answer"]
