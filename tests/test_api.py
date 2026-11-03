"""
API tests for the Solar Automation server.

Run from the repo root:
    pip install -r requirements-dev.txt
    pytest -v
"""

from fastapi.testclient import TestClient
from api_server import app

client = TestClient(app)


def test_calculate_happy_path():
    """Valid input returns a full system proposal."""
    resp = client.post("/calculate", json={
        "name": "Test", "monthly_consumption_kwh": 350,
        "orientation": "south", "location": "bratislava",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["system"]["power_kwp"] > 0
    assert body["customer"]["name"] == "Test"


def test_calculate_rejects_non_numeric_consumption():
    """Wrong type is a schema error (422), not a server crash (500)."""
    resp = client.post("/calculate", json={"monthly_consumption_kwh": "abc"})
    assert resp.status_code == 422


def test_calculate_rejects_impossible_values():
    """Valid JSON but outside business rules gives 400 with every error listed."""
    resp = client.post("/calculate", json={
        "monthly_consumption_kwh": 0, "orientation": "up",
    })
    assert resp.status_code == 400
    assert len(resp.json()["detail"]) == 2  # too low + unknown orientation


def test_generate_proposal_returns_pdf():
    """The /calculate output can be sent as-is and produces a real PDF."""
    calc = client.post("/calculate", json={"monthly_consumption_kwh": 350}).json()
    resp = client.post("/generate-proposal", json=calc)
    assert resp.status_code == 200
    url = resp.json()["proposal_pdf"]["download_url"]
    pdf = client.get(url)
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF")
