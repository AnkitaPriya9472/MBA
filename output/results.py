"""Simulation results container and query interface.

Story 19: SimulationResult with query methods and save/load functionality.
"""

from typing import Any
from pathlib import Path
import json
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from models.scenario import ShockScenario
from models.world_state import WorldState
from models.agent_types import RoundResponse
from models.events import WorldEvent


class SimulationResult(BaseModel):
    """Queryable container for completed simulation data.
    
    This is the primary output artifact of a simulation run.
    All query methods are read-only and maintain simulation integrity.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    scenario: ShockScenario
    rounds_completed: int
    world_state: WorldState
    metadata: dict[str, Any]  # model_used, duration_seconds, timestamp, total_fallbacks
    
    def get_round(self, n: int) -> dict[str, RoundResponse]:
        """Get all agent responses for a specific round.
        
        Args:
            n: Round number (1-indexed)
            
        Returns:
            Dictionary mapping agent_id to RoundResponse
        """
        return self.world_state.round_responses.get(n, {})
    
    def get_agent_history(self, agent_id: str) -> list[RoundResponse]:
        """Get all responses for a specific agent across all rounds.
        
        Args:
            agent_id: The agent's unique identifier
            
        Returns:
            List of RoundResponse objects chronologically ordered
        """
        history = []
        for round_num in sorted(self.world_state.round_responses.keys()):
            if agent_id in self.world_state.round_responses[round_num]:
                history.append(self.world_state.round_responses[round_num][agent_id])
        return history
    
    def get_events(self, event_type: str | None = None) -> list[WorldEvent]:
        """Get simulation events, optionally filtered by type.
        
        Args:
            event_type: Optional filter for specific event type
            
        Returns:
            List of WorldEvent objects
        """
        if event_type is None:
            return self.world_state.events
        return [e for e in self.world_state.events if e.event_type == event_type]
    
    def get_capture_timeline(self) -> dict[str, list[float]]:
        """Get capture score progression for all agents.
        
        Returns:
            Dictionary mapping agent_id to list of capture scores per round
        """
        timeline: dict[str, list[float]] = {}
        
        for round_num in sorted(self.world_state.round_responses.keys()):
            for agent_id, state in self.world_state.agent_states.items():
                if agent_id not in timeline:
                    timeline[agent_id] = []
                # Capture score is stored in agent state
                timeline[agent_id].append(state.capture_score)
        
        return timeline
    
    def get_price_timeline(self, commodity: str) -> list[float]:
        """Get price history for a specific commodity.
        
        Args:
            commodity: Commodity identifier (e.g., "steel_hrc", "iron_ore")
            
        Returns:
            List of spot prices per round
        """
        if commodity not in self.world_state.market_states:
            return []
        
        market_state = self.world_state.market_states[commodity]
        return market_state.price_history
    
    def get_trade_flow_evolution(self) -> dict[str, list[float]]:
        """Get trade flow volume evolution for all routes.
        
        Returns:
            Dictionary mapping route_key (from-to-commodity) to volume per round
        """
        # This requires tracking historical trade routes per round
        # For now, return current routes
        evolution: dict[str, list[float]] = {}
        
        for route in self.world_state.trade_routes:
            route_key = f"{route.from_country}-{route.to_country}-{route.commodity}"
            if route_key not in evolution:
                evolution[route_key] = []
            evolution[route_key].append(route.volume)
        
        return evolution
    
    def save(self, path: str) -> None:
        """Save simulation results to JSON file.
        
        Args:
            path: File path to save to
        """
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Serialize to JSON-compatible format
        data = self.model_dump(mode="json")
        
        # Handle datetime serialization
        if "timestamp" in data["metadata"]:
            if isinstance(data["metadata"]["timestamp"], datetime):
                data["metadata"]["timestamp"] = data["metadata"]["timestamp"].isoformat()
        
        with output_path.open("w") as f:
            json.dump(data, f, indent=2)
    
    @classmethod
    def load(cls, path: str) -> "SimulationResult":
        """Load simulation results from JSON file.
        
        Args:
            path: File path to load from
            
        Returns:
            SimulationResult instance
        """
        content = Path(path).read_text()
        data = json.loads(content)
        
        # Handle datetime deserialization
        if "timestamp" in data["metadata"]:
            if isinstance(data["metadata"]["timestamp"], str):
                data["metadata"]["timestamp"] = datetime.fromisoformat(data["metadata"]["timestamp"])
        
        return cls.model_validate(data)
