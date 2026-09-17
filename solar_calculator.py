"""
Solar Panel System Calculator
Calculation module for photovoltaic systems in Slovakia

Inputs: monthly consumption, roof type, orientation, location
Outputs: system power, panel count, annual production, price, ROI
"""

# ============================================================
# CONFIGURATION - adjust these values per supplier
# ============================================================

# Price per 1 kWp of installed system (EUR)
PRICE_PER_KWP = 1100

# Power of one panel (Wp) - standard 2024-2026
PANEL_POWER_WP = 450

# Average electricity price in Slovakia (EUR/kWh)
ELECTRICITY_PRICE = 0.18

# Annual panel degradation (%)
ANNUAL_DEGRADATION = 0.005

# Percentage of self-consumption from produced energy
SELF_CONSUMPTION_RATIO = 0.70

# Coefficients by roof orientation (south = 100%)
ORIENTATION_COEFFICIENT = {
    "south": 1.00,
    "southwest": 0.95,
    "southeast": 0.95,
    "west": 0.85,
    "east": 0.85,
    "northeast": 0.80,
    "northwest": 0.80,
    "north": 0.60,
}

# Average annual production in Slovakia (kWh per 1 kWp) by region
# Source: PVGIS database for Slovakia
PRODUCTION_KWH_PER_KWP = {
    "bratislava": 1150,
    "trnava": 1140,
    "nitra": 1130,
    "trencin": 1080,
    "zilina": 1050,
    "banska_bystrica": 1070,
    "presov": 1030,
    "kosice": 1060,
    "default": 1100,
}

# Limits
MIN_CONSUMPTION_KWH = 50
MAX_CONSUMPTION_KWH = 5000
MAX_POWER_WITHOUT_PERMIT_KWP = 10.8  # Slovak legislation


# ============================================================
# MAIN CALCULATION FUNCTION
# ============================================================

def calculate_system(
    monthly_consumption_kwh: float,
    orientation: str = "south",
    roof_type: str = "sloped",
    location: str = "default",
    wants_battery: bool = False,
    budget_limit: float = None,
) -> dict:
    """
    Main function - calculates a complete PV system proposal.

    Args:
        monthly_consumption_kwh: Customer's monthly consumption in kWh
        orientation: Roof orientation (south, west, east, etc.)
        roof_type: "sloped" or "flat"
        location: Region in Slovakia
        wants_battery: Whether the customer wants battery storage
        budget_limit: Customer's maximum budget (EUR)

    Returns:
        dict with complete system proposal
    """

    # --- INPUT VALIDATION ---
    errors = validate_inputs(monthly_consumption_kwh, orientation, location)
    if errors:
        return {"success": False, "errors": errors}

    # --- ANNUAL CONSUMPTION ---
    annual_consumption = monthly_consumption_kwh * 12

    # --- ORIENTATION COEFFICIENT ---
    orient_coef = ORIENTATION_COEFFICIENT.get(orientation.lower(), 0.85)

    # --- REGIONAL PRODUCTION ---
    production_per_kwp = PRODUCTION_KWH_PER_KWP.get(
        location.lower(), PRODUCTION_KWH_PER_KWP["default"]
    )

    # Actual production adjusted for orientation
    actual_production_per_kwp = production_per_kwp * orient_coef

    # --- OPTIMAL SYSTEM POWER ---
    # Goal: cover 90-100% of annual consumption
    optimal_power_kwp = annual_consumption / actual_production_per_kwp
    optimal_power_kwp = round(optimal_power_kwp, 1)

    # Check legislative limit
    over_limit = optimal_power_kwp > MAX_POWER_WITHOUT_PERMIT_KWP
    if over_limit:
        limit_note = (
            f"Warning: system {optimal_power_kwp} kWp exceeds the limit of "
            f"{MAX_POWER_WITHOUT_PERMIT_KWP} kWp - requires permit from the distribution company."
        )
    else:
        limit_note = None

    # --- PANEL COUNT ---
    panel_count = round((optimal_power_kwp * 1000) / PANEL_POWER_WP)
    # Recalculate actual power based on whole panels
    actual_power_kwp = round((panel_count * PANEL_POWER_WP) / 1000, 2)

    # --- ANNUAL PRODUCTION ---
    annual_production = round(actual_power_kwp * actual_production_per_kwp)

    # --- SYSTEM PRICE ---
    system_price = round(actual_power_kwp * PRICE_PER_KWP)

    # Battery (optional)
    battery_price = 0
    battery_capacity = 0
    if wants_battery:
        # Rule: approx 1 kWh battery per 1 kWp system
        battery_capacity = round(actual_power_kwp)
        battery_price = battery_capacity * 500  # ~500 EUR per kWh

    total_price = system_price + battery_price

    # --- BUDGET CHECK ---
    over_budget = False
    if budget_limit and total_price > budget_limit:
        over_budget = True

    # --- ROI / PAYBACK ---
    annual_savings = round(annual_production * SELF_CONSUMPTION_RATIO * ELECTRICITY_PRICE)
    if annual_savings > 0:
        payback_years = round(total_price / annual_savings, 1)
    else:
        payback_years = None

    # --- 25-YEAR SAVINGS ---
    savings_25_years = 0
    for year in range(1, 26):
        degradation = (1 - ANNUAL_DEGRADATION) ** year
        savings_25_years += annual_production * degradation * SELF_CONSUMPTION_RATIO * ELECTRICITY_PRICE
    savings_25_years = round(savings_25_years)
    net_profit_25_years = savings_25_years - total_price

    # --- CONFIDENCE SCORE ---
    confidence = calculate_confidence(
        monthly_consumption_kwh, orientation, location, roof_type
    )

    # --- RESULT ---
    return {
        "success": True,
        "system": {
            "power_kwp": actual_power_kwp,
            "panel_count": panel_count,
            "panel_power_wp": PANEL_POWER_WP,
            "annual_production_kwh": annual_production,
            "orientation": orientation,
            "location": location,
        },
        "financials": {
            "system_price_eur": system_price,
            "battery_price_eur": battery_price,
            "battery_kwh": battery_capacity,
            "total_price_eur": total_price,
            "annual_savings_eur": annual_savings,
            "payback_years": payback_years,
            "savings_25_years_eur": savings_25_years,
            "net_profit_25_years_eur": net_profit_25_years,
            "over_budget": over_budget,
        },
        "metadata": {
            "confidence_score": confidence,
            "over_distribution_limit": over_limit,
            "note": limit_note,
        },
    }


# ============================================================
# VALIDATION
# ============================================================

def validate_inputs(consumption, orientation, location) -> list:
    """Check if inputs are within realistic ranges."""
    errors = []

    if consumption < MIN_CONSUMPTION_KWH:
        errors.append(f"Consumption {consumption} kWh is too low (min {MIN_CONSUMPTION_KWH} kWh).")
    if consumption > MAX_CONSUMPTION_KWH:
        errors.append(f"Consumption {consumption} kWh is too high (max {MAX_CONSUMPTION_KWH} kWh).")
    if orientation.lower() not in ORIENTATION_COEFFICIENT:
        errors.append(
            f"Unknown orientation '{orientation}'. "
            f"Options: {', '.join(ORIENTATION_COEFFICIENT.keys())}"
        )
    return errors


# ============================================================
# CONFIDENCE SCORE
# ============================================================

def calculate_confidence(consumption, orientation, location, roof_type) -> int:
    """
    Confidence score 0-100%.
    Higher = more reliable estimate, lower = needs human review.
    """
    score = 100

    # Extreme consumption lowers confidence
    if consumption < 100 or consumption > 2000:
        score -= 15

    # Suboptimal orientation = less predictable result
    if orientation.lower() in ("north", "west", "east"):
        score -= 10

    # Unknown location
    if location.lower() not in PRODUCTION_KWH_PER_KWP:
        score -= 10

    # Flat roof = more complex installation
    if roof_type.lower() == "flat":
        score -= 5

    return max(score, 0)


# ============================================================
# DEMO - TEST
# ============================================================

if __name__ == "__main__":
    # Example customer from presentation: 350 kWh/month, sloped roof, south
    result = calculate_system(
        monthly_consumption_kwh=350,
        orientation="south",
        roof_type="sloped",
        location="trnava",
        wants_battery=False,
        budget_limit=None,
    )

    if result["success"]:
        s = result["system"]
        f = result["financials"]
        m = result["metadata"]

        print("=" * 50)
        print("  SOLAR SYSTEM PROPOSAL")
        print("=" * 50)
        print(f"  System power:      {s['power_kwp']} kWp")
        print(f"  Panel count:       {s['panel_count']}x {s['panel_power_wp']}Wp")
        print(f"  Annual production: {s['annual_production_kwh']} kWh")
        print(f"  Orientation:       {s['orientation']}")
        print(f"  Location:          {s['location']}")
        print("-" * 50)
        print(f"  System price:      {f['system_price_eur']} EUR")
        if f["battery_price_eur"] > 0:
            print(f"  Battery ({f['battery_kwh']} kWh):  {f['battery_price_eur']} EUR")
        print(f"  TOTAL PRICE:       {f['total_price_eur']} EUR")
        print(f"  Annual savings:    {f['annual_savings_eur']} EUR")
        print(f"  Payback period:    {f['payback_years']} years")
        print(f"  25-year savings:   {f['savings_25_years_eur']} EUR")
        print(f"  Net profit (25y):  {f['net_profit_25_years_eur']} EUR")
        print("-" * 50)
        print(f"  Confidence score:  {m['confidence_score']}%")
        if m["note"]:
            print(f"  Warning: {m['note']}")
        print("=" * 50)
    else:
        print("ERROR:", result["errors"])