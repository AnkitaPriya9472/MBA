"""Shock scenario model and loader.

Story 5: ShockScenario - the external event that drives the simulation.
"""

from typing import Any, Literal
from pathlib import Path
import json

from pydantic import BaseModel, field_validator


class ShockScenario(BaseModel):
    """External shock event configuration.
    
    This defines the economic disruption that agents must respond to.
    The 'context' field is injected verbatim into every agent's prompt.
    """
    id: str
    name: str
    description: str
    category: Literal["tariff", "supply_shock", "regulatory", "financial", "diplomatic", "natural_disaster"]
    severity: float  # 0.0–1.0
    affected_sectors: list[str]
    context: str  # Narrative paragraph for LLM prompts (write like Reuters brief)
    initial_market_impacts: dict[str, float] = {}  # commodity → price multiplier
    duration_rounds: int | None = None  # None = indefinite
    initiating_country: str | None = None
    initial_parameters: dict[str, Any] = {}  # tariff_rate_pct, target_country, etc.
    
    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: float) -> float:
        """Ensure severity is in valid range."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("severity must be between 0.0 and 1.0")
        return v
    
    @classmethod
    def from_json(cls, path: str) -> "ShockScenario":
        """Load scenario from JSON file."""
        content = Path(path).read_text()
        data = json.loads(content)
        return cls.model_validate(data)
