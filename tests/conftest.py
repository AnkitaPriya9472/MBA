"""Shared pytest fixtures for all test files.

Story 20: Test fixtures - provides reusable test data and mocks.
"""

import pytest
from datetime import datetime

from models.agent_types import (
    AgentProfile, AgentState, AgentType, RoundResponse,
    CompanyAction, GovernmentAction, PublicSignal, PrivateIntent
)
from models.world_state import WorldState
from models.market import MarketState, TradeRoute
from models.scenario import ShockScenario
from models.events import WorldEvent


@pytest.fixture
def minimal_company_profile() -> AgentProfile:
    """Minimal valid company agent profile."""
    return AgentProfile(
        agent_id="test_company",
        name="Test Steel Company",
        agent_type=AgentType.company,
        description="A test company for unit testing",
        objectives=[
            "Maximize revenue",
            "Maintain market share",
            "Protect US export volumes"
        ],
        constraints=[
            "Board approval required for capex > $1Bn",
            "Must maintain debt-to-equity < 1.5"
        ],
        data={
            "revenue_usd_bn": 10.0,
            "ebitda_margin_pct": 15.0,
            "us_export_volume_mt": 500000,
            "cash_reserves_usd_bn": 2.0,
            "cash_usd_mn": 2000,  # For parser tests
            "debt_to_equity": 0.8,
            "primary_markets": ["US", "EU"],
            "lobbying_budget_usd_mn": 25,
            "financial_health": 0.75,
            "fear_greed_index": 5.0,
            "loss_aversion_multiplier": 2.0,
            "herd_tendency": 0.4,
            "risk_appetite": "moderate"
        },
        country="IN",
        information_completeness=0.9,
        direct_partners=["gov_india", "iron_ore"],
        home_government_id="gov_india"
    )


@pytest.fixture
def minimal_government_profile() -> AgentProfile:
    """Minimal valid government agent profile."""
    return AgentProfile(
        agent_id="gov_india",
        name="Government of India",
        agent_type=AgentType.government,
        description="Test government for unit testing",
        objectives=[
            "Protect domestic steel industry",
            "Maintain WTO compliance"
        ],
        constraints=[
            "WTO commitments limit retaliatory tariff rates",
            "Fiscal deficit ceiling at 6% GDP"
        ],
        data={
            "fiscal_deficit_pct_gdp": 5.0,
            "wto_member": True,
            "financial_health": 0.75,
            "fear_greed_index": 4.5
        },
        country="IN",
        information_completeness=0.95
    )


@pytest.fixture
def minimal_world_state(
    minimal_company_profile: AgentProfile,
    minimal_government_profile: AgentProfile
) -> WorldState:
    """Minimal world state with 2 agents and 1 market."""
    company_state = AgentState.initial(minimal_company_profile)
    gov_state = AgentState.initial(minimal_government_profile)
    
    steel_market = MarketState(
        commodity="steel_hrc",
        spot_price=650.0,
        prev_price=680.0,
        price_change_pct=-4.4,
        demand=1000000.0,
        supply=950000.0,
        volume_cleared=950000.0,
        unmet_demand=50000.0,
        unmet_demand_pct=5.0,
        price_history=[700.0, 680.0, 650.0]
    )
    
    trade_route = TradeRoute(
        from_country="IN",
        to_country="US",
        commodity="steel_hrc",
        volume=500000.0,
        tariff_rate=25.0,
        friction=0.15
    )
    
    return WorldState(
        current_round=1,
        scenario_name="test_scenario",
        agent_profiles={
            "test_company": minimal_company_profile,
            "gov_india": minimal_government_profile
        },
        agent_states={
            "test_company": company_state,
            "gov_india": gov_state
        },
        market_states={"steel_hrc": steel_market},
        trade_routes=[trade_route],
        all_signals=[],
        events=[],
        round_responses={}
    )


@pytest.fixture
def sample_round_response() -> RoundResponse:
    """Sample round response with default values."""
    return RoundResponse(
        agent_id="test_company",
        round=1,
        primary_action="export_diversion",
        secondary_action=None,
        assessment="Testing export diversion to ASEAN markets due to US tariffs.",
        confidence=0.75,
        impact_areas=["revenue", "market_share"],
        metrics_change={"revenue_change_pct": -5.0, "margin_change_pct": -2.0},
        signals_to_ecosystem=[
            PublicSignal(
                from_agent="test_company",
                to_agent=None,
                content="Announcing diversion of 200K MT to ASEAN",
                signal_type="announcement",
                round=1
            )
        ],
        private_intent=PrivateIntent(
            content="Will also explore EU joint venture options",
            target_agent=None
        ),
        raw_llm_output='{"action_id": "export_diversion", ...}',
        is_fallback=False
    )


@pytest.fixture
def sample_tariff_shock() -> ShockScenario:
    """Sample tariff shock scenario."""
    return ShockScenario(
        id="test_tariff_shock",
        name="US 50% Tariff on Indian Steel",
        description="Test tariff shock",
        category="tariff",
        severity=0.85,
        affected_sectors=["steel", "manufacturing"],
        context="The United States has imposed a 50% tariff on steel imports from India.",
        initial_market_impacts={"steel_hrc": 0.72},
        initiating_country="US",
        initial_parameters={
            "tariff_rate_pct": 50,
            "target_country": "IN"
        }
    )


@pytest.fixture
def sample_public_signal() -> PublicSignal:
    """Sample public signal."""
    return PublicSignal(
        from_agent="test_company",
        to_agent=None,
        content="Diversifying export markets to reduce US dependency",
        signal_type="announcement",
        round=1
    )


@pytest.fixture
def sample_world_event() -> WorldEvent:
    """Sample world event."""
    return WorldEvent(
        event_type="MARKET_FLOOD",
        round=2,
        description="India-ASEAN steel route volume surged 45%",
        affected_agents=["test_company", "asean_consumer"],
        data={"volume_increase_pct": 45.0, "route": "IN-SEA"}
    )
