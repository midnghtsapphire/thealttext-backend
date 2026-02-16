"""
TheAltText — Carbon Tracking Utility
Estimates and tracks carbon footprint of AI operations.
Supports the eco-tracking feature.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class CarbonEstimate:
    """Carbon footprint estimate for an operation."""
    co2_mg: float  # milligrams of CO2
    energy_wh: float  # watt-hours
    equivalent_trees_seconds: float  # seconds of tree absorption equivalent
    description: str


# Average estimates based on published research on AI inference costs
ESTIMATES = {
    "vision_inference_free": CarbonEstimate(
        co2_mg=0.5,
        energy_wh=0.001,
        equivalent_trees_seconds=0.02,
        description="Free-tier vision model inference",
    ),
    "vision_inference_paid": CarbonEstimate(
        co2_mg=2.0,
        energy_wh=0.004,
        equivalent_trees_seconds=0.08,
        description="Paid vision model inference",
    ),
    "web_scan_page": CarbonEstimate(
        co2_mg=0.3,
        energy_wh=0.0006,
        equivalent_trees_seconds=0.012,
        description="Single page web scan",
    ),
    "report_generation": CarbonEstimate(
        co2_mg=0.1,
        energy_wh=0.0002,
        equivalent_trees_seconds=0.004,
        description="Report PDF/CSV generation",
    ),
}


def estimate_carbon(operation: str, count: int = 1) -> CarbonEstimate:
    """Get carbon estimate for an operation."""
    base = ESTIMATES.get(operation, CarbonEstimate(0.1, 0.0002, 0.004, "Unknown operation"))
    return CarbonEstimate(
        co2_mg=round(base.co2_mg * count, 3),
        energy_wh=round(base.energy_wh * count, 6),
        equivalent_trees_seconds=round(base.equivalent_trees_seconds * count, 4),
        description=f"{count}x {base.description}",
    )


def format_carbon_savings(total_mg: float) -> dict:
    """Format carbon data for display."""
    return {
        "co2_mg": round(total_mg, 2),
        "co2_grams": round(total_mg / 1000, 4),
        "trees_equivalent_minutes": round(total_mg / 1000 / 22 * 60, 2),  # avg tree absorbs ~22g CO2/day
        "lightbulb_seconds": round(total_mg / 1000 / 36 * 3600, 2),  # 60W bulb = ~36g CO2/hour
        "message": f"This session used approximately {round(total_mg, 1)}mg of CO2 — less than a single breath.",
    }
