"""
Solar Automation API Server
Exposes calculator and PDF generator as HTTP endpoints for n8n.

Endpoints:
    POST /calculate        - Calculate solar system from customer data
    POST /generate-proposal - Generate PDF proposal and return file path
    GET  /health           - Health check
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, field_validator
from typing import Optional, Union
from solar_calculator import calculate_system
from proposal_generator import generate_proposal
import os
import uuid
from datetime import datetime

app = FastAPI(title="Solar Automation API", version="1.0.0")

# Directory for generated PDFs
PDF_DIR = os.getenv("PDF_DIR", "/app/generated_pdfs")
os.makedirs(PDF_DIR, exist_ok=True)


# ============================================================
# REQUEST / RESPONSE MODELS
# ============================================================

class CalculateRequest(BaseModel):
    """Input from n8n form submission."""
    name: str = "Customer"
    email: str = ""
    phone: str = ""
    monthly_consumption_kwh: Union[str, float] = 350
    roof_type: str = "sloped"
    orientation: str = "south"
    location: str = "default"
    wants_battery: str = "No"
    budget_limit: Optional[Union[str, float]] = None

    @field_validator("monthly_consumption_kwh", "budget_limit", mode="before")
    def convert_to_float(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            try:
                return float(v)
            except ValueError:
                return v
        return v


class ProposalRequest(BaseModel):
    """
    Input for PDF proposal generation.

    Preferred: send the /calculate output as-is (system, financials,
    metadata, customer). Flat customer_* fields override customer{}.
    Flat numeric fields are a fallback when system/financials are missing.
    """
    system: Optional[dict] = None
    financials: Optional[dict] = None
    metadata: Optional[dict] = None
    customer: Optional[dict] = None
    customer_name: str = ""
    customer_email: str = ""
    customer_phone: str = ""
    system_power_kwp: Union[str, float] = 3.6
    panel_count: Union[str, int] = 8
    annual_production_kwh: Union[str, float] = 4140
    system_price_eur: Union[str, float] = 3960
    payback_years: Union[str, float] = 7.9
    annual_savings_eur: Union[str, float] = 554
    company_name: str = "Solar Solutions s.r.o."
    company_phone: str = "+421 900 000 000"
    company_email: str = "info@solarsolutions.sk"

    @field_validator(
        "system_power_kwp",
        "panel_count",
        "annual_production_kwh",
        "system_price_eur",
        "payback_years",
        "annual_savings_eur",
        mode="before",
    )
    def convert_numbers(cls, v):
        """Convert string numbers to float/int."""
        if v is None:
            return None
        if isinstance(v, str):
            try:
                # Try int first for panel_count
                if "." not in v:
                    return int(v)
                return float(v)
            except (ValueError, AttributeError):
                return v
        return v


# ============================================================
# ENDPOINTS
# ============================================================

@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.post("/calculate")
def calculate(req: CalculateRequest):
    """
    Calculate optimal solar system based on customer inputs.
    Called by n8n after form submission.
    """
    battery = req.wants_battery
    if isinstance(battery, str):
        battery = battery.lower() in ("yes", "true", "1", "ano")

    location = req.location.strip().lower()

    result = calculate_system(
        monthly_consumption_kwh=req.monthly_consumption_kwh,
        orientation=req.orientation.strip().lower(),
        roof_type=req.roof_type.strip().lower(),
        location=location,
        wants_battery=battery,
        budget_limit=req.budget_limit,
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["errors"])

    result["customer"] = {
        "name": req.name,
        "email": req.email,
        "phone": req.phone,
    }

    return result


@app.post("/generate-proposal")
def create_proposal(req: ProposalRequest):
    """
    Generate PDF proposal from calculation data passed from n8n.
    Returns the calculation result + PDF download URL.
    """
    nested = req.customer or {}
    customer_name = (req.customer_name or nested.get("name") or "Customer").strip()
    customer_email = (req.customer_email or nested.get("email") or "").strip()
    customer_phone = (req.customer_phone or nested.get("phone") or "").strip()

    if req.system and req.financials:
        result = {
            "success": True,
            "system": req.system,
            "financials": req.financials,
            "metadata": req.metadata or {
                "confidence_score": 90,
                "over_distribution_limit": False,
                "note": None,
            },
        }
    else:
        result = build_result_from_flat(req)

    file_id = uuid.uuid4().hex[:8]
    filename = f"proposal_{file_id}.pdf"
    filepath = os.path.join(PDF_DIR, filename)

    generate_proposal(
        result=result,
        customer_name=customer_name,
        customer_email=customer_email,
        customer_phone=customer_phone,
        company_name=req.company_name,
        company_phone=req.company_phone,
        company_email=req.company_email,
        output_path=filepath,
    )

    result["customer"] = {
        "name": customer_name,
        "email": customer_email,
        "phone": customer_phone,
    }
    result["proposal_pdf"] = {
        "filename": filename,
        "download_url": f"/download/{filename}",
    }

    return result


def build_result_from_flat(req: ProposalRequest) -> dict:
    """Legacy path: rebuild a calculator-shaped result from flat fields."""
    # Ensure numeric fields are floats/ints
    system_power_kwp = float(req.system_power_kwp) if req.system_power_kwp else 3.6
    panel_count = int(req.panel_count) if req.panel_count else 8
    annual_production_kwh = float(req.annual_production_kwh) if req.annual_production_kwh else 4140
    system_price_eur = float(req.system_price_eur) if req.system_price_eur else 3960
    payback_years = float(req.payback_years) if req.payback_years else 7.9
    annual_savings_eur = float(req.annual_savings_eur) if req.annual_savings_eur else 554

    result = {
        "success": True,
        "system": {
            "power_kwp": system_power_kwp,
            "panel_count": panel_count,
            "panel_power_wp": 450,
            "annual_production_kwh": annual_production_kwh,
            "orientation": "south",
            "location": "default"
        },
        "financials": {
            "system_price_eur": system_price_eur,
            "battery_price_eur": 0,
            "battery_kwh": 0,
            "total_price_eur": system_price_eur,
            "annual_savings_eur": annual_savings_eur,
            "payback_years": payback_years,
            "savings_25_years_eur": int(annual_savings_eur * 25),
            "net_profit_25_years_eur": int(annual_savings_eur * 25 - system_price_eur),
            "over_budget": False
        },
        "metadata": {
            "confidence_score": 90,
            "over_distribution_limit": False,
            "note": None
        }
    }

    return result


@app.get("/download/{filename}")
def download_pdf(filename: str):
    """Download a generated PDF proposal."""
    filepath = os.path.join(PDF_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="PDF not found")
    return FileResponse(filepath, media_type="application/pdf", filename=filename)


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
