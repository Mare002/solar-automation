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
from pydantic import BaseModel, Field
from typing import Optional
from solar_calculator import calculate_system
from proposal_generator import generate_proposal
import os
import uuid
from datetime import datetime

app = FastAPI(title="Solar Automation API", version="1.0.0")

# Directory for generated PDFs
PDF_DIR = "/app/generated_pdfs"
os.makedirs(PDF_DIR, exist_ok=True)


# ============================================================
# REQUEST / RESPONSE MODELS
# ============================================================

class CalculateRequest(BaseModel):
    """Input from n8n form submission."""
    model_config = {"coerce_numbers_to_str": True}

    name: str = "Customer"
    email: str = ""
    phone: str = ""
    monthly_consumption_kwh: float = 350
    roof_type: str = "sloped"        # "sloped" or "flat"
    orientation: str = "south"        # south, southwest, etc.
    location: str = "default"         # city or region
    wants_battery: str = "No"
    budget_limit: Optional[float] = None


class ProposalRequest(BaseModel):
    """Input for PDF proposal generation."""
    model_config = {"coerce_numbers_to_str": True}

    name: str = "Customer"
    email: str = ""
    phone: str = ""
    monthly_consumption_kwh: float = 350
    roof_type: str = "sloped"
    orientation: str = "south"
    location: str = "default"
    wants_battery: str = "No"
    budget_limit: Optional[float] = None
    company_name: str = "Solar Solutions s.r.o."
    company_phone: str = "+421 900 000 000"
    company_email: str = "info@solarsolutions.sk"


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
    # Map form values to calculator inputs
    battery = req.wants_battery
    if isinstance(battery, str):
        battery = battery.lower() in ("yes", "true", "1", "ano")

    # Clean location - remove whitespace/newlines
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

    # Add customer info to response (for n8n to use downstream)
    result["customer"] = {
        "name": req.name,
        "email": req.email,
        "phone": req.phone,
    }

    return result


@app.post("/generate-proposal")
def create_proposal(req: ProposalRequest):
    """
    Calculate system AND generate PDF proposal.
    Returns the calculation result + PDF download URL.
    """
    # Map form values
    battery = req.wants_battery
    if isinstance(battery, str):
        battery = battery.lower() in ("yes", "true", "1", "ano")

    # Clean location
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

    # Generate unique filename
    file_id = uuid.uuid4().hex[:8]
    filename = f"proposal_{file_id}.pdf"
    filepath = os.path.join(PDF_DIR, filename)

    # Generate PDF
    generate_proposal(
        result=result,
        customer_name=req.name,
        customer_email=req.email,
        company_name=req.company_name,
        company_phone=req.company_phone,
        company_email=req.company_email,
        output_path=filepath,
    )

    # Return result + PDF download link
    result["customer"] = {
        "name": req.name,
        "email": req.email,
        "phone": req.phone,
    }
    result["proposal_pdf"] = {
        "filename": filename,
        "download_url": f"/download/{filename}",
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
