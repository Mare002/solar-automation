"""
Solar System Proposal - PDF Generator
Creates a professional PDF proposal from calculator results.

Usage:
    python proposal_generator.py

Dependencies:
    pip install reportlab
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import Table, TableStyle
from solar_calculator import calculate_system
from datetime import datetime, timedelta


# ============================================================
# COLORS & STYLING
# ============================================================

PRIMARY = HexColor("#1a5276")      # Dark blue
SECONDARY = HexColor("#2e86c1")    # Lighter blue
ACCENT = HexColor("#27ae60")       # Green for positive numbers
TEXT_DARK = HexColor("#2c3e50")    # Dark text
TEXT_LIGHT = HexColor("#7f8c8d")   # Gray text
WHITE = HexColor("#ffffff")
LIGHT_BG = HexColor("#f0f4f8")    # Light background for sections


# ============================================================
# PDF GENERATOR
# ============================================================

def generate_proposal(
    result: dict,
    customer_name: str = "Customer",
    customer_email: str = "",
    company_name: str = "Solar Solutions s.r.o.",
    company_phone: str = "+421 900 000 000",
    company_email: str = "info@solarsolutions.sk",
    output_path: str = "proposal.pdf",
    validity_days: int = 30,
):
    """
    Generate a professional PDF proposal from calculator results.

    Args:
        result: Output from calculate_system()
        customer_name: Customer's name
        customer_email: Customer's email
        company_name: Your company name
        company_phone: Company phone number
        company_email: Company email
        output_path: Where to save the PDF
        validity_days: How many days the offer is valid
    """

    if not result["success"]:
        print(f"ERROR: Cannot generate proposal - {result['errors']}")
        return None

    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4  # 595 x 842 points

    sys = result["system"]
    fin = result["financials"]
    meta = result["metadata"]

    today = datetime.now()
    valid_until = today + timedelta(days=validity_days)
    proposal_id = f"PV-{today.strftime('%Y%m%d')}-001"

    # ── PAGE 1: HEADER & SYSTEM OVERVIEW ──

    # Top color bar
    c.setFillColor(PRIMARY)
    c.rect(0, height - 80, width, 80, fill=True, stroke=False)

    # Company name
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(30, height - 45, company_name)

    # Subtitle
    c.setFont("Helvetica", 10)
    c.drawString(30, height - 62, f"{company_phone}  |  {company_email}")

    # Proposal title
    c.setFillColor(TEXT_DARK)
    c.setFont("Helvetica-Bold", 26)
    c.drawString(30, height - 120, "Solar System Proposal")

    # Proposal metadata
    c.setFont("Helvetica", 10)
    c.setFillColor(TEXT_LIGHT)
    c.drawString(30, height - 140, f"Proposal ID: {proposal_id}")
    c.drawString(30, height - 155, f"Date: {today.strftime('%d.%m.%Y')}")
    c.drawString(30, height - 170, f"Valid until: {valid_until.strftime('%d.%m.%Y')}")

    # Customer info box
    c.setFillColor(LIGHT_BG)
    c.roundRect(30, height - 230, width - 60, 45, 5, fill=True, stroke=False)

    c.setFillColor(TEXT_DARK)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(40, height - 205, f"Prepared for: {customer_name}")
    c.setFont("Helvetica", 10)
    if customer_email:
        c.drawString(40, height - 220, f"Email: {customer_email}")

    # ── SYSTEM OVERVIEW SECTION ──
    y = height - 270
    c.setFillColor(PRIMARY)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(30, y, "Recommended System")

    y -= 10
    c.setStrokeColor(SECONDARY)
    c.setLineWidth(2)
    c.line(30, y, 200, y)

    # System specs - visual cards
    y -= 45
    card_width = (width - 80) / 3

    specs = [
        ("System Power", f"{sys['power_kwp']} kWp", "Optimal for your consumption"),
        ("Panel Count", f"{sys['panel_count']}x {sys['panel_power_wp']}Wp", "High-efficiency panels"),
        ("Annual Production", f"{sys['annual_production_kwh']} kWh", f"Based on {sys['location'].title()} region"),
    ]

    for i, (title, value, subtitle) in enumerate(specs):
        x = 30 + i * (card_width + 10)

        # Card background
        c.setFillColor(LIGHT_BG)
        c.roundRect(x, y - 15, card_width, 70, 5, fill=True, stroke=False)

        # Value (big number)
        c.setFillColor(PRIMARY)
        c.setFont("Helvetica-Bold", 18)
        c.drawString(x + 10, y + 30, value)

        # Title
        c.setFillColor(TEXT_DARK)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(x + 10, y + 12, title)

        # Subtitle
        c.setFillColor(TEXT_LIGHT)
        c.setFont("Helvetica", 7)
        c.drawString(x + 10, y - 2, subtitle)

    # ── CONFIGURATION DETAILS ──
    y -= 60
    c.setFillColor(TEXT_DARK)
    c.setFont("Helvetica", 10)

    details = [
        ("Roof orientation:", sys["orientation"].title()),
        ("Location:", sys["location"].title()),
        ("Self-consumption ratio:", "70%"),
    ]

    for label, value in details:
        c.setFont("Helvetica", 10)
        c.setFillColor(TEXT_LIGHT)
        c.drawString(40, y, label)
        c.setFillColor(TEXT_DARK)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(200, y, value)
        y -= 18

    # ── FINANCIAL OVERVIEW SECTION ──
    y -= 25
    c.setFillColor(PRIMARY)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(30, y, "Financial Overview")

    y -= 10
    c.setStrokeColor(SECONDARY)
    c.setLineWidth(2)
    c.line(30, y, 200, y)

    # Price breakdown table
    y -= 30

    table_data = [
        ["Item", "Amount"],
        ["Photovoltaic system", f"{fin['system_price_eur']:,} EUR"],
    ]

    if fin["battery_price_eur"] > 0:
        table_data.append(
            [f"Battery storage ({fin['battery_kwh']} kWh)", f"{fin['battery_price_eur']:,} EUR"]
        )

    table_data.append(["TOTAL PRICE", f"{fin['total_price_eur']:,} EUR"])

    table = Table(table_data, colWidths=[350, 170])
    table.setStyle(TableStyle([
        # Header row
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        # Total row (last row)
        ("BACKGROUND", (0, -1), (-1, -1), LIGHT_BG),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, -1), (-1, -1), 11),
        # All rows
        ("FONTNAME", (0, 1), (-1, -2), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -2), 10),
        ("TEXTCOLOR", (0, 1), (-1, -1), TEXT_DARK),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, TEXT_LIGHT),
    ]))

    table_width, table_height = table.wrap(0, 0)
    table.drawOn(c, 30, y - table_height)
    y = y - table_height - 30

    # ROI section header
    c.setFillColor(PRIMARY)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(30, y, "Return on Investment")

    y -= 10
    c.setStrokeColor(SECONDARY)
    c.setLineWidth(2)
    c.line(30, y, 220, y)

    y -= 55

    # ROI highlights
    roi_cards = [
        ("Annual Savings", f"{fin['annual_savings_eur']} EUR", ACCENT),
        ("Payback Period", f"{fin['payback_years']} years", SECONDARY),
        ("25-Year Net Profit", f"{fin['net_profit_25_years_eur']:,} EUR", ACCENT),
    ]

    card_width = (width - 80) / 3
    card_height = 50
    for i, (title, value, color) in enumerate(roi_cards):
        x = 30 + i * (card_width + 10)

        # Card background
        c.setFillColor(LIGHT_BG)
        c.roundRect(x, y, card_width, card_height, 3, fill=True, stroke=False)

        # Colored top accent bar
        c.setFillColor(color)
        c.rect(x, y + card_height - 4, card_width, 4, fill=True, stroke=False)

        # Value (big number)
        c.setFillColor(color)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(x + 10, y + 20, value)

        # Label
        c.setFillColor(TEXT_DARK)
        c.setFont("Helvetica", 9)
        c.drawString(x + 10, y + 6, title)

    # ── CONFIDENCE & WARNINGS ──
    y -= 40
    c.setFillColor(TEXT_DARK)
    c.setFont("Helvetica", 9)
    c.drawString(30, y, f"Estimate confidence: {meta['confidence_score']}%")

    if meta["note"]:
        y -= 15
        c.setFillColor(HexColor("#e74c3c"))
        c.setFont("Helvetica-Bold", 9)
        c.drawString(30, y, meta["note"])

    if fin["over_budget"]:
        y -= 15
        c.setFillColor(HexColor("#e74c3c"))
        c.setFont("Helvetica-Bold", 9)
        c.drawString(30, y, "Note: Total price exceeds the specified budget limit.")

    # ── FOOTER ──
    c.setFillColor(PRIMARY)
    c.rect(0, 0, width, 35, fill=True, stroke=False)
    c.setFillColor(WHITE)
    c.setFont("Helvetica", 8)
    c.drawString(30, 14, f"{company_name}  |  {company_phone}  |  {company_email}")
    c.drawRightString(width - 30, 14, "Page 1 of 1")

    # ── SAVE ──
    c.save()
    print(f"Proposal saved: {output_path}")
    return output_path


# ============================================================
# DEMO - TEST
# ============================================================

if __name__ == "__main__":
    # Calculate system for demo customer
    result = calculate_system(
        monthly_consumption_kwh=350,
        orientation="south",
        roof_type="sloped",
        location="trnava",
        wants_battery=True,
        budget_limit=None,
    )

    # Generate PDF proposal
    generate_proposal(
        result=result,
        customer_name="Marko Macek",
        customer_email="marko@example.com",
        company_name="Solar Solutions s.r.o.",
        company_phone="+421 900 123 456",
        company_email="info@solarsolutions.sk",
        output_path="proposal.pdf",
    )