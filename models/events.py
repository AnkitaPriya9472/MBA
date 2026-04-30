"""World events that emerge from simulation dynamics.

Story 4: WorldEvent model and event type constants.
"""

from typing import Any
from pydantic import BaseModel


# Event type constants
CAPTURE_TIPPING_POINT = "CAPTURE_TIPPING_POINT"
MARKET_FLOOD = "MARKET_FLOOD"
TRADE_WAR_ESCALATION = "TRADE_WAR_ESCALATION"
SUPPLY_SHOCK = "SUPPLY_SHOCK"
VALUATION_COLLAPSE = "VALUATION_COLLAPSE"
DIPLOMATIC_BREAKDOWN = "DIPLOMATIC_BREAKDOWN"


class WorldEvent(BaseModel):
    """An emergent event detected by the simulation.
    
    Events are triggered by threshold crossings or pattern detection
    in the state resolver.
    """
    event_type: str
    round: int
    description: str
    affected_agents: list[str]
    data: dict[str, Any] = {}
