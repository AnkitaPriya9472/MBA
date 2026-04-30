"""Core agent types and response models for the MBA simulation.

This module defines:
- AgentType enum (Story 2)
- AgentProfile (Story 2) - immutable agent configuration
- AgentState (Story 2) - mutable per-round agent state
- Action enums for all 6 agent types (Story 3)
- PublicSignal, PrivateIntent (Story 3)
- RoundResponse (Story 3) - structured LLM output
"""

from enum import Enum
from typing import Any, Literal
from pathlib import Path
import json

from pydantic import BaseModel, ConfigDict, field_validator


# ============================================================================
# Story 2: AgentType Enum and Core Models
# ============================================================================

class AgentType(str, Enum):
    """Six agent role types in the simulation."""
    company = "company"
    government = "government"
    regulator = "regulator"
    consumer = "consumer"
    supplier = "supplier"
    investor = "investor"


class AgentProfile(BaseModel):
    """Immutable agent configuration loaded from JSON.
    
    This represents the agent's permanent identity, objectives, and constraints.
    """
    model_config = ConfigDict(frozen=True)
    
    agent_id: str
    name: str
    agent_type: AgentType
    description: str
    objectives: list[str]
    constraints: list[str]
    data: dict[str, Any]  # Role-specific data (financials, policy tools, etc.)
    country: str  # ISO-2 country code
    information_completeness: float = 1.0  # 0.0–1.0
    direct_partners: list[str] = []  # agent_ids of direct trading partners
    home_government_id: str | None = None  # for company/consumer/supplier agents
    
    @classmethod
    def from_json(cls, path: str) -> "AgentProfile":
        """Load agent profile from JSON file."""
        content = Path(path).read_text()
        data = json.loads(content)
        return cls.model_validate(data)


class AgentState(BaseModel):
    """Mutable agent state updated each round.
    
    This tracks the agent's evolving financial health, sentiment, relationships,
    and action history throughout the simulation.
    """
    model_config = ConfigDict(extra="allow")  # Resolver can attach computed fields
    
    agent_id: str
    current_round: int = 0
    fear_greed_index: float = 5.0  # 0 (extreme fear) to 10 (extreme greed)
    capture_score: float = 0.0  # 0.0–1.0+, relevant for regulators/govts
    financial_health: float = 0.7  # 0.0–1.0
    active_actions: list[str] = []  # in-progress action IDs
    completed_actions: list[str] = []
    relationships: dict[str, float] = {}  # agent_id → trust score
    metrics: dict[str, float] = {}  # KPIs: revenue_change_pct, margin, etc.
    signals_sent: list[str] = []
    
    @classmethod
    def initial(cls, profile: AgentProfile) -> "AgentState":
        """Create initial state from profile at round 0."""
        return cls(
            agent_id=profile.agent_id,
            current_round=0,
            fear_greed_index=profile.data.get("fear_greed_index", 5.0),
            capture_score=0.0,
            financial_health=profile.data.get("financial_health", 0.7),
            active_actions=[],
            completed_actions=[],
            relationships={},
            metrics={},
            signals_sent=[]
        )
    
    def apply_updates(self, patch: dict) -> None:
        """Apply partial updates from resolver."""
        for key, value in patch.items():
            setattr(self, key, value)


# ============================================================================
# Story 3: Action Enums for All 6 Agent Types
# ============================================================================

class CompanyAction(str, Enum):
    """Actions available to company agents."""
    export_diversion = "export_diversion"
    joint_venture = "joint_venture"
    fdi = "fdi"
    licensing = "licensing"
    domestic_expansion = "domestic_expansion"
    price_war = "price_war"
    lobby_government = "lobby_government"
    hedge = "hedge"
    wait_and_observe = "wait_and_observe"


class GovernmentAction(str, Enum):
    """Actions available to government agents."""
    retaliatory_tariff = "retaliatory_tariff"
    subsidy = "subsidy"
    wto_dispute = "wto_dispute"
    trade_negotiation = "trade_negotiation"
    capital_controls = "capital_controls"
    stimulus = "stimulus"
    do_nothing = "do_nothing"


class RegulatorAction(str, Enum):
    """Actions available to regulator agents."""
    open_investigation = "open_investigation"
    impose_provisional_duty = "impose_provisional_duty"
    recommend_definitive_duty = "recommend_definitive_duty"
    reject_petition = "reject_petition"
    issue_cautionary_note = "issue_cautionary_note"


class ConsumerAction(str, Enum):
    """Actions available to consumer agents."""
    switch_suppliers = "switch_suppliers"
    stockpile = "stockpile"
    absorb_cost = "absorb_cost"
    pass_through_pricing = "pass_through_pricing"
    demand_subsidy = "demand_subsidy"


class SupplierAction(str, Enum):
    """Actions available to supplier agents."""
    raise_prices = "raise_prices"
    hold_prices = "hold_prices"
    lower_prices = "lower_prices"
    diversify_customers = "diversify_customers"
    capacity_investment = "capacity_investment"
    negotiate_long_term = "negotiate_long_term"


class InvestorAction(str, Enum):
    """Actions available to investor agents."""
    buy = "buy"
    sell = "sell"
    short = "short"
    fx_bet = "fx_bet"
    sector_rotation = "sector_rotation"
    wait = "wait"


# ============================================================================
# Story 3: Signal and Intent Models
# ============================================================================

class PublicSignal(BaseModel):
    """A public signal broadcast to other agents in the ecosystem."""
    from_agent: str
    to_agent: str | None = None  # None = broadcast to all
    content: str
    signal_type: str  # "announcement", "policy", "market_signal", etc.
    round: int


class PrivateIntent(BaseModel):
    """Private agent intent NEVER shared with other agents.
    
    Only visible to the simulation observer (dashboard).
    """
    content: str
    target_agent: str | None = None


# ============================================================================
# Story 3: RoundResponse - Structured LLM Output
# ============================================================================

class RoundResponse(BaseModel):
    """Structured response from an agent for a single round.
    
    This is the canonical output format every LLM call must produce.
    """
    agent_id: str
    round: int
    primary_action: str  # Coerced to valid action string by parser
    secondary_action: str | None = None
    assessment: str  # Narrative reasoning, max 500 chars
    confidence: float  # 0.0–1.0
    impact_areas: list[str]
    metrics_change: dict[str, float] = {}
    signals_to_ecosystem: list[PublicSignal] = []
    private_intent: PrivateIntent | None = None
    raw_llm_output: str | None = None
    is_fallback: bool = False
    
    @classmethod
    def fallback(cls, agent_id: str, round: int) -> "RoundResponse":
        """Create a safe fallback response when LLM fails.
        
        Returns a conservative "wait" action with low confidence.
        """
        return cls(
            agent_id=agent_id,
            round=round,
            primary_action="wait_and_observe",  # Safe default for most agent types
            secondary_action=None,
            assessment="[FALLBACK] LLM failed to produce valid response after retries.",
            confidence=0.3,
            impact_areas=[],
            metrics_change={},
            signals_to_ecosystem=[],
            private_intent=None,
            raw_llm_output=None,
            is_fallback=True
        )
