"""Market and trade models for the simulation.

Story 4: MarketState and TradeRoute models.
"""

from pydantic import BaseModel


class MarketState(BaseModel):
    """State of a commodity market at a point in time."""
    commodity: str
    spot_price: float
    prev_price: float | None = None
    price_change_pct: float | None = None
    demand: float
    supply: float
    volume_cleared: float
    unmet_demand: float
    unmet_demand_pct: float
    price_history: list[float] = []


class TradeRoute(BaseModel):
    """A bilateral trade route between two countries for a commodity."""
    from_country: str
    to_country: str
    commodity: str
    volume: float
    tariff_rate: float  # percentage
    friction: float  # 0.0–1.0, higher = more friction/cost
