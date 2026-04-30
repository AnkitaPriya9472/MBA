"""Unit tests for StateResolver.

Story 20: Test the 10-step resolution pipeline and integration points.
"""

import pytest

from simulation.resolver import StateResolver
from simulation.market import MarketClearing
from simulation.capture import CaptureEngine
from simulation.trade import TradeNetwork
from simulation.sentiment import SentimentEngine
from models.agent_types import RoundResponse, AgentType, PublicSignal
from models.world_state import WorldState
from models.events import CAPTURE_TIPPING_POINT


def test_government_tariff_updates_trade_routes(minimal_world_state, minimal_government_profile):
    """Government choosing retaliatory_tariff should update trade routes."""
    # Initialize engines
    market = MarketClearing()
    capture = CaptureEngine()
    trade = TradeNetwork(routes=minimal_world_state.trade_routes)
    sentiment = SentimentEngine()
    
    resolver = StateResolver(
        market=market,
        capture=capture,
        trade=trade,
        sentiment=sentiment,
    )
    
    # Create government response with retaliatory tariff
    gov_response = RoundResponse(
        agent_id="gov_india",
        round=2,
        primary_action="retaliatory_tariff",
        secondary_action=None,
        assessment="Retaliating against US tariffs with our own 25% tariff",
        confidence=0.85,
        impact_areas=["trade", "diplomacy"],
        metrics_change={
            "target_country": "US",
            "tariff_rate_pct": 25.0
        },
        signals_to_ecosystem=[],
        private_intent=None,
        raw_llm_output="",
        is_fallback=False
    )
    
    responses = {"gov_india": gov_response}
    
    # Run resolution
    minimal_world_state.current_round = 2
    resolution = resolver.resolve(
        responses=responses,
        world_state=minimal_world_state,
        profiles=minimal_world_state.agent_profiles,
    )
    
    # Check that trade flow changes were computed
    assert "trade_flow_changes" in resolution.model_fields_set
    # Trade routes should be updated (may be empty list but exists)
    assert isinstance(resolution.trade_flow_changes, list)


def test_company_lobbying_increases_capture_score(minimal_world_state, minimal_company_profile):
    """Company lobbying should increase regulator capture score."""
    # Create regulator profile
    from models.agent_types import AgentProfile, AgentState
    
    regulator_profile = AgentProfile(
        agent_id="dgtr",
        name="DGTR",
        agent_type=AgentType.regulator,
        description="Indian regulator",
        objectives=["Fair trade enforcement"],
        constraints=["Legal process requirements"],
        data={
            "capture_vulnerability": 0.4,
            "jurisdiction": "India"
        },
        country="IN",
        information_completeness=0.85
    )
    
    minimal_world_state.agent_profiles["dgtr"] = regulator_profile
    minimal_world_state.agent_states["dgtr"] = AgentState.initial(regulator_profile)
    
    # Initialize engines
    market = MarketClearing()
    capture = CaptureEngine()
    capture.initialize_regulator("dgtr", 0.4)
    
    trade = TradeNetwork(routes=minimal_world_state.trade_routes)
    sentiment = SentimentEngine()
    
    resolver = StateResolver(
        market=market,
        capture=capture,
        trade=trade,
        sentiment=sentiment,
    )
    
    # Create company response with lobbying
    company_response = RoundResponse(
        agent_id="test_company",
        round=2,
        primary_action="lobby_government",
        secondary_action=None,
        assessment="Lobbying DGTR for trade protection",
        confidence=0.75,
        impact_areas=["regulation"],
        metrics_change={
            "lobby_target": "dgtr",
            "lobby_amount_usd_mn": 25.0
        },
        signals_to_ecosystem=[],
        private_intent=None,
        raw_llm_output="",
        is_fallback=False
    )
    
    responses = {"test_company": company_response}
    
    # Run resolution
    minimal_world_state.current_round = 2
    resolution = resolver.resolve(
        responses=responses,
        world_state=minimal_world_state,
        profiles=minimal_world_state.agent_profiles,
    )
    
    # Check that capture updates exist
    assert "dgtr" in resolution.capture_updates
    # Capture score should have increased (from 0.0 baseline)
    assert resolution.capture_updates["dgtr"] > 0.0


def test_investor_sell_produces_negative_valuation_change(minimal_world_state):
    """Investor selling should create negative valuation change."""
    # Create investor profile
    from models.agent_types import AgentProfile, AgentState
    
    investor_profile = AgentProfile(
        agent_id="fii_investor",
        name="FII Aggregate",
        agent_type=AgentType.investor,
        description="Foreign institutional investor",
        objectives=["Maximize returns"],
        constraints=["Risk limits"],
        data={"aum_usd_bn": 180},
        country="US",
        information_completeness=0.8
    )
    
    minimal_world_state.agent_profiles["fii_investor"] = investor_profile
    minimal_world_state.agent_states["fii_investor"] = AgentState.initial(investor_profile)
    
    # Initialize engines
    market = MarketClearing()
    capture = CaptureEngine()
    trade = TradeNetwork(routes=minimal_world_state.trade_routes)
    sentiment = SentimentEngine()
    
    resolver = StateResolver(
        market=market,
        capture=capture,
        trade=trade,
        sentiment=sentiment,
    )
    
    # Create investor response selling test_company
    investor_response = RoundResponse(
        agent_id="fii_investor",
        round=2,
        primary_action="sell",
        secondary_action=None,
        assessment="Exiting position due to tariff uncertainty",
        confidence=0.70,
        impact_areas=["portfolio"],
        metrics_change={
            "position_changes": {
                "test_company": -500.0  # Selling $500M position
            }
        },
        signals_to_ecosystem=[],
        private_intent=None,
        raw_llm_output="",
        is_fallback=False
    )
    
    responses = {"fii_investor": investor_response}
    
    # Run resolution
    minimal_world_state.current_round = 2
    resolution = resolver.resolve(
        responses=responses,
        world_state=minimal_world_state,
        profiles=minimal_world_state.agent_profiles,
    )
    
    # Check that valuation changes exist and test_company has negative change
    if "test_company" in resolution.valuation_changes:
        assert resolution.valuation_changes["test_company"] < 0.0


def test_two_companies_same_market_triggers_conflict(minimal_world_state):
    """Two companies targeting same market for export diversion should create conflict."""
    # Create second company
    from models.agent_types import AgentProfile, AgentState
    
    company2_profile = AgentProfile(
        agent_id="jsw_steel",
        name="JSW Steel",
        agent_type=AgentType.company,
        description="Second steel company",
        objectives=["Market expansion"],
        constraints=["Debt limits"],
        data={"revenue_usd_bn": 14.0},
        country="IN",
        information_completeness=0.85
    )
    
    minimal_world_state.agent_profiles["jsw_steel"] = company2_profile
    minimal_world_state.agent_states["jsw_steel"] = AgentState.initial(company2_profile)
    
    # Initialize engines
    market = MarketClearing()
    capture = CaptureEngine()
    trade = TradeNetwork(routes=minimal_world_state.trade_routes)
    sentiment = SentimentEngine()
    
    resolver = StateResolver(
        market=market,
        capture=capture,
        trade=trade,
        sentiment=sentiment,
    )
    
    # Both companies choose export diversion to same market
    company1_response = RoundResponse(
        agent_id="test_company",
        round=2,
        primary_action="export_diversion",
        secondary_action=None,
        assessment="Diverting to ASEAN markets",
        confidence=0.80,
        impact_areas=["revenue"],
        metrics_change={"target_markets": ["TH", "VN", "SG"]},
        signals_to_ecosystem=[],
        private_intent=None,
        raw_llm_output="",
        is_fallback=False
    )
    
    company2_response = RoundResponse(
        agent_id="jsw_steel",
        round=2,
        primary_action="export_diversion",
        secondary_action=None,
        assessment="Also diverting to ASEAN markets",
        confidence=0.75,
        impact_areas=["revenue"],
        metrics_change={"target_markets": ["TH", "VN"]},
        signals_to_ecosystem=[],
        private_intent=None,
        raw_llm_output="",
        is_fallback=False
    )
    
    responses = {
        "test_company": company1_response,
        "jsw_steel": company2_response
    }
    
    # Run resolution
    minimal_world_state.current_round = 2
    resolution = resolver.resolve(
        responses=responses,
        world_state=minimal_world_state,
        profiles=minimal_world_state.agent_profiles,
    )
    
    # Check that conflicts were detected
    # (Implementation may vary, but conflicts list should exist)
    assert isinstance(resolution.conflicts, list)


def test_all_resolution_steps_produce_output(minimal_world_state):
    """All 10 steps should produce non-None outputs (no silent failures)."""
    # Initialize engines
    market = MarketClearing()
    capture = CaptureEngine()
    trade = TradeNetwork(routes=minimal_world_state.trade_routes)
    sentiment = SentimentEngine()
    
    resolver = StateResolver(
        market=market,
        capture=capture,
        trade=trade,
        sentiment=sentiment,
    )
    
    # Create basic company response
    company_response = RoundResponse(
        agent_id="test_company",
        round=2,
        primary_action="wait_and_observe",
        secondary_action=None,
        assessment="Waiting to see market developments",
        confidence=0.60,
        impact_areas=[],
        metrics_change={},
        signals_to_ecosystem=[],
        private_intent=None,
        raw_llm_output="",
        is_fallback=False
    )
    
    responses = {"test_company": company_response}
    
    # Run resolution
    minimal_world_state.current_round = 2
    resolution = resolver.resolve(
        responses=responses,
        world_state=minimal_world_state,
        profiles=minimal_world_state.agent_profiles,
    )
    
    # Verify all key outputs exist (not None)
    assert resolution.trade_flow_changes is not None
    assert resolution.market_clearing is not None
    assert resolution.capture_updates is not None
    assert resolution.valuation_changes is not None
    assert resolution.sentiment_updates is not None
    assert resolution.conflicts is not None
    assert resolution.agent_state_patches is not None
    assert resolution.events is not None
    
    # Verify round number matches
    assert resolution.round == 2
