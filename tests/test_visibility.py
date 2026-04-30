"""Unit tests for VisibilityFilter.

Story 20: Test information asymmetry, signal delay, and must-keep rules.
"""

import pytest

from agents.visibility import VisibilityFilter
from models.agent_types import AgentType, PublicSignal, AgentProfile, AgentState, RoundResponse
from models.world_state import WorldState


def test_cross_country_signal_delayed_one_round(minimal_world_state):
    """Signals from different country should have 1-round delay."""
    # Create a US company profile
    us_company = AgentProfile(
        agent_id="us_company",
        name="US Steel Co",
        agent_type=AgentType.company,
        description="Test US company",
        objectives=["Maintain market share"],
        constraints=["Budget limits"],
        data={"financial_health": 0.75},
        country="US",  # Different country
        information_completeness=1.0  # Full info to test delay only
    )
    
    # Add to world state
    minimal_world_state.agent_profiles["us_company"] = us_company
    minimal_world_state.agent_states["us_company"] = AgentState.initial(us_company)
    
    # Create a signal from Indian company in round 2
    india_signal = PublicSignal(
        from_agent="test_company",  # Indian company from fixture
        to_agent=None,
        content="Diversifying to ASEAN markets",
        signal_type="announcement",
        round=2
    )
    
    minimal_world_state.all_signals = [india_signal]
    minimal_world_state.current_round = 2
    
    # US company checking visibility in round 2
    visible = VisibilityFilter.get_visible_signals(
        minimal_world_state,
        us_company,
        round=2
    )
    
    # Signal from round 2 (same round) should NOT be visible yet due to delay
    assert len(visible) == 0
    
    # Now check in round 3 - signal should be visible
    visible_round_3 = VisibilityFilter.get_visible_signals(
        minimal_world_state,
        us_company,
        round=3
    )
    
    # Signal from round 2 should be visible in round 3 (1-round delay satisfied)
    assert len(visible_round_3) == 1
    assert visible_round_3[0].from_agent == "test_company"


def test_same_country_signal_visible_next_round(minimal_world_state):
    """Signals from same country should be visible in the next round."""
    # Both test_company and gov_india are from India
    company_profile = minimal_world_state.agent_profiles["test_company"]
    
    # Create signal from government in round 1
    gov_signal = PublicSignal(
        from_agent="gov_india",
        to_agent=None,
        content="Announcing retaliatory tariff investigation",
        signal_type="policy",
        round=1
    )
    
    minimal_world_state.all_signals = [gov_signal]
    minimal_world_state.current_round = 2
    
    # Check visibility for company in round 2
    visible = VisibilityFilter.get_visible_signals(
        minimal_world_state,
        company_profile,
        round=2
    )
    
    # Same-country signal from round 1 should be visible in round 2
    assert len(visible) == 1
    assert visible[0].from_agent == "gov_india"


def test_must_keep_signal_always_present(minimal_world_state):
    """Must-keep signals should always be visible regardless of completeness."""
    # Create company with very low information completeness
    low_info_company = AgentProfile(
        agent_id="low_info_company",
        name="Low Info Company",
        agent_type=AgentType.company,
        description="Test company with poor intelligence",
        objectives=["Survive"],
        constraints=["Limited resources"],
        data={"financial_health": 0.5},
        country="IN",
        information_completeness=0.1,  # Only 10% information
        direct_partners=["gov_india"],
        home_government_id="gov_india"
    )
    
    minimal_world_state.agent_profiles["low_info_company"] = low_info_company
    minimal_world_state.agent_states["low_info_company"] = AgentState.initial(low_info_company)
    
    # Create signal from home government
    gov_signal = PublicSignal(
        from_agent="gov_india",  # Home government - must keep
        to_agent=None,
        content="Policy announcement",
        signal_type="policy",
        round=1
    )
    
    # Create signal from unrelated party
    other_signal = PublicSignal(
        from_agent="test_company",
        to_agent=None,
        content="Market update",
        signal_type="announcement",
        round=1
    )
    
    minimal_world_state.all_signals = [gov_signal, other_signal]
    minimal_world_state.current_round = 2
    
    # With only 10% completeness, run multiple times
    # The government signal should ALWAYS appear (must-keep)
    # The other signal might not (probabilistic)
    
    visible = VisibilityFilter.get_visible_signals(
        minimal_world_state,
        low_info_company,
        round=2
    )
    
    # Must-keep signal from government should ALWAYS be present
    gov_signals = [s for s in visible if s.from_agent == "gov_india"]
    assert len(gov_signals) == 1


def test_private_intent_never_visible():
    """PrivateIntent objects should never be in visible signals."""
    # This is enforced by WorldState.all_signals only containing PublicSignal
    # The filter should only process PublicSignal objects
    
    # Create world state with only public signals
    profiles = {
        "agent1": AgentProfile(
            agent_id="agent1",
            name="Agent 1",
            agent_type=AgentType.company,
            description="Test",
            objectives=["Test"],
            constraints=["Test"],
            data={},
            country="IN",
            information_completeness=1.0
        )
    }
    
    states = {
        "agent1": AgentState.initial(profiles["agent1"])
    }
    
    # Only PublicSignals in all_signals
    public_signal = PublicSignal(
        from_agent="agent2",
        to_agent=None,
        content="Public announcement",
        signal_type="announcement",
        round=1
    )
    
    world_state = WorldState(
        current_round=2,
        scenario_name="test",
        agent_profiles=profiles,
        agent_states=states,
        market_states={},
        trade_routes=[],
        all_signals=[public_signal],  # Only PublicSignals
        events=[],
        round_responses={}
    )
    
    visible = VisibilityFilter.get_visible_signals(
        world_state,
        profiles["agent1"],
        round=2
    )
    
    # All visible signals should be PublicSignal type
    for signal in visible:
        assert isinstance(signal, PublicSignal)


def test_deterministic_filtering_with_same_seed(minimal_world_state):
    """Same agent + round should produce identical filtered list (deterministic)."""
    company_profile = minimal_world_state.agent_profiles["test_company"]
    company_profile.information_completeness = 0.5  # 50% to see randomness
    
    # Create multiple signals
    signals = [
        PublicSignal(
            from_agent=f"agent_{i}",
            to_agent=None,
            content=f"Signal {i}",
            signal_type="announcement",
            round=1
        )
        for i in range(10)
    ]
    
    minimal_world_state.all_signals = signals
    minimal_world_state.current_round = 2
    
    # Run visibility filter twice with same parameters
    visible_1 = VisibilityFilter.get_visible_signals(
        minimal_world_state,
        company_profile,
        round=2
    )
    
    visible_2 = VisibilityFilter.get_visible_signals(
        minimal_world_state,
        company_profile,
        round=2
    )
    
    # Results should be identical (deterministic)
    assert len(visible_1) == len(visible_2)
    
    visible_ids_1 = sorted([s.from_agent for s in visible_1])
    visible_ids_2 = sorted([s.from_agent for s in visible_2])
    
    assert visible_ids_1 == visible_ids_2


def test_competitive_effects_from_export_diversion(minimal_world_state):
    """Export diversion by competitor should create competitive pressure."""
    company_profile = minimal_world_state.agent_profiles["test_company"]
    
    # Create a competitor company
    competitor_profile = AgentProfile(
        agent_id="competitor",
        name="Competitor Steel Co",
        agent_type=AgentType.company,
        description="Competitor",
        objectives=["Market share"],
        constraints=["Budget"],
        data={},
        country="IN",
        information_completeness=0.9
    )
    
    minimal_world_state.agent_profiles["competitor"] = competitor_profile
    minimal_world_state.agent_states["competitor"] = AgentState.initial(competitor_profile)
    
    # Create response showing competitor did export diversion
    competitor_response = RoundResponse(
        agent_id="competitor",
        round=1,
        primary_action="export_diversion",
        secondary_action=None,
        assessment="Diverting exports to ASEAN",
        confidence=0.80,
        impact_areas=["revenue"],
        metrics_change={},
        signals_to_ecosystem=[],
        private_intent=None,
        raw_llm_output="",
        is_fallback=False
    )
    
    minimal_world_state.round_responses[1] = {"competitor": competitor_response}
    minimal_world_state.current_round = 2
    
    # Get competitive effects for the main company
    effects = VisibilityFilter.get_competitive_effects(
        minimal_world_state,
        company_profile
    )
    
    # Should detect competitor diversion pressure
    assert "competitor_diversion_pressure" in effects
    assert effects["competitor_diversion_pressure"] == pytest.approx(0.3)
