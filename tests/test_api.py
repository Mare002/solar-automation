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


def test_confidence_lowered_for_every_weak_orientation():
    """All orientations under 90 % production lose 10 points; south-ish ones do not."""
    def score(orientation):
        return client.post("/calculate", json={
            "monthly_consumption_kwh": 350, "wants_battery": "No",
            "orientation": orientation, "location": "bratislava",
        }).json()["metadata"]["confidence_score"]

    for o in ("south", "southeast", "southwest"):
        assert score(o) == 100, o
    for o in ("east", "west", "northeast", "northwest", "north"):
        assert score(o) == 90, o


def _calc(**fields):
    body = {"monthly_consumption_kwh": 350, "wants_battery": "No", "location": "bratislava", **fields}
    return client.post("/calculate", json=body).json()


def test_roof_types_from_form_are_mapped():
    """Every roof option in the form maps to sloped / flat / other."""
    expected = {
        "Sloped (pitched)": "sloped", "Metal": "sloped", "Tile": "sloped",
        "Flat": "flat", "Concrete": "flat", "Other": "other",
    }
    for label, roof in expected.items():
        assert _calc(roof_type=label)["system"]["roof_type"] == roof, label


def test_roof_type_affects_confidence():
    """Flat and unknown roofs need more checking than a pitched roof."""
    assert _calc(roof_type="Tile")["metadata"]["confidence_score"] == 100
    assert _calc(roof_type="Concrete")["metadata"]["confidence_score"] == 95
    assert _calc(roof_type="Other")["metadata"]["confidence_score"] == 95


def test_region_names_with_diacritics_are_recognised():
    """Dropdown labels (with diacritics and spaces) hit the regional production table."""
    for label, key in {"Banská Bystrica": "banska_bystrica", "Trenčín": "trencin",
                       "Žilina": "zilina", "Prešov": "presov", "Košice": "kosice"}.items():
        res = _calc(location=label)
        assert res["system"]["location"] == key, label
        assert res["metadata"]["confidence_score"] == 100, label
    assert _calc(location="Other")["metadata"]["confidence_score"] == 90


def test_battery_accepts_slovak_yes():
    """The chatbot may send "áno"; it must count as a battery, "nie" must not."""
    assert _calc(wants_battery="áno")["financials"]["battery_price_eur"] > 0
    assert _calc(wants_battery="Áno")["financials"]["battery_price_eur"] > 0
    assert _calc(wants_battery="nie")["financials"]["battery_price_eur"] == 0
