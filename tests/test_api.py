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
        "name": "Test", "monthly_consumption_kwh": 350, "wants_battery": "No",
        "orientation": "south", "location": "bratislava",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["system"]["power_kwp"] > 0
    assert body["customer"]["name"] == "Test"


def test_calculate_rejects_non_numeric_consumption():
    """Wrong type is a schema error (422), not a server crash (500)."""
    resp = client.post("/calculate", json={"monthly_consumption_kwh": "abc", "wants_battery": "No"})
    assert resp.status_code == 422


def test_calculate_rejects_impossible_values():
    """Valid JSON but outside business rules gives 400 with every error listed."""
    resp = client.post("/calculate", json={
        "monthly_consumption_kwh": 0, "wants_battery": "No", "orientation": "up",
    })
    assert resp.status_code == 400
    assert len(resp.json()["detail"]) == 2  # too low + unknown orientation


def test_generate_proposal_returns_pdf():
    """The /calculate output can be sent as-is and produces a real PDF."""
    calc = client.post("/calculate", json={"monthly_consumption_kwh": 350, "wants_battery": "No"}).json()
    resp = client.post("/generate-proposal", json=calc)
    assert resp.status_code == 200
    url = resp.json()["proposal_pdf"]["download_url"]
    pdf = client.get(url)
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF")


def test_calculate_rejects_misspelled_fields():
    """Old n8n keys (monthly_kwh, battery) must fail loudly, not fall back to defaults."""
    resp = client.post("/calculate", json={"monthly_kwh": 234, "battery": "Yes"})
    assert resp.status_code == 422
    missing = {e["loc"][-1] for e in resp.json()["detail"]}
    assert missing == {"monthly_consumption_kwh", "wants_battery"}


def test_calculate_battery_changes_price():
    """Battery "Yes" adds the battery to the total, "No" does not."""
    base = {"monthly_consumption_kwh": 234, "location": "bratislava"}
    no = client.post("/calculate", json={**base, "wants_battery": "No"}).json()["financials"]
    yes = client.post("/calculate", json={**base, "wants_battery": "Yes"}).json()["financials"]
    assert no["battery_price_eur"] == 0
    assert yes["battery_price_eur"] > 0
    assert yes["total_price_eur"] == no["total_price_eur"] + yes["battery_price_eur"]


def test_generate_proposal_keeps_battery_from_calculate():
    """Sending the whole /calculate output keeps battery, orientation and location."""
    calc = client.post("/calculate", json={
        "monthly_consumption_kwh": 100, "wants_battery": "Yes",
        "orientation": "East", "location": "Bratislava",
    }).json()
    prop = client.post("/generate-proposal", json=calc).json()
    assert prop["financials"] == calc["financials"]
    assert prop["system"]["orientation"] == "east"
    assert prop["system"]["location"] == "bratislava"


def test_generate_proposal_flat_fields_keep_battery():
    """Legacy flat path: battery is added to the total instead of being dropped."""
    prop = client.post("/generate-proposal", json={
        "customer_name": "Jana", "system_power_kwp": 1.35, "panel_count": 3,
        "annual_production_kwh": 1320, "system_price_eur": 1485,
        "battery_price_eur": 500, "battery_kwh": 1,
        "payback_years": 12, "annual_savings_eur": 166,
        "orientation": "east", "location": "bratislava",
    }).json()
    fin = prop["financials"]
    assert fin["battery_price_eur"] == 500
    assert fin["total_price_eur"] == 1985
    assert prop["system"]["orientation"] == "east"
