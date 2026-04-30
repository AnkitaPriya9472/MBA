"""Global world state and round execution models.

Story 4: WorldState, RoundContext, and RoundResolution.
"""

from typing import Any
from pydantic import BaseModel

from models.agent_types import AgentProfile, AgentState, RoundResponse, PublicSignal
from models.market import MarketState, TradeRoute
from models.events import WorldEvent


class WorldState(BaseModel):
    """God-view of the entire simulation state.
    
    This is the authoritative source of truth for all simulation data.
    """
    current_round: int = 0
    scenario_name: str
    agent_profiles: dict[str, AgentProfile]  # agent_id → profile
    agent_states: dict[str, AgentState]  # agent_id → mutable state
    market_states: dict[str, MarketState]  # commodity → MarketState
    trade_routes: list[TradeRoute]
    all_signals: list[PublicSignal]  # Every public signal ever produced
    events: list[WorldEvent]
    round_responses: dict[int, dict[str, RoundResponse]] = {}  # round → agent_id → response
    
    def get_agent_state(self, agent_id: str) -> AgentState:
        """Get current state for an agent."""
        return self.agent_states[agent_id]
    
    def get_signals_for_round(self, round: int) -> list[PublicSignal]:
        """Get all signals produced in a specific round."""
        return [s for s in self.all_signals if s.round == round]
    
    def get_responses_for_round(self, round: int) -> dict[str, RoundResponse]:
        """Get all agent responses for a specific round."""
        return self.round_responses.get(round, {})


class RoundContext(BaseModel):
    """Per-agent input context for a single round.
    
    This is what each agent sees when making its decision.
    Information asymmetry is enforced via the VisibilityFilter.
    """
    agent_id: str
    round: int
    shock: dict[str, Any]  # Scenario context
    visible_signals: list[PublicSignal]  # Filtered by information completeness
    market_state: dict[str, MarketState]
    competitive_effects: dict[str, float]  # Computed pressure from competitors
    impacts_on_agent: dict[str, Any]
    own_state: AgentState
    capture_bias: str | None = None  # Injected if agent is captured


class RoundResolution(BaseModel):
    """Post-resolution state changes for a round.
    
    This is the output of the StateResolver after processing all agent responses.
    """
    round: int
    trade_flow_changes: list[TradeRoute]
    market_clearing: dict[str, MarketState]
    capture_updates: dict[str, float]  # agent_id → new capture_score
    valuation_changes: dict[str, float]  # agent_id → valuation % change
    sentiment_updates: dict[str, float]  # agent_id → new fear_greed_index
    conflicts: list[dict]
    agent_state_patches: dict[str, dict]  # agent_id → partial patch dict
    events: list[WorldEvent]
