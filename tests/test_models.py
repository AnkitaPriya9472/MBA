"""Unit tests for core models (Stories 2-5).

Tests:
- AgentProfile immutability and from_json loading
- AgentState initialization and updates
- RoundResponse fallback creation
- ShockScenario severity validation
- WorldState helper methods
"""

import json
import pytest
from pathlib import Path
import tempfile

from models.agent_types import (
    AgentType, AgentProfile, AgentState, RoundResponse,
    CompanyAction, GovernmentAction, PublicSignal, PrivateIntent
)
from models.scenario import ShockScenario
from models.world_state import WorldState, RoundContext, RoundResolution
from models.market import MarketState, TradeRoute
from models.events import WorldEvent, CAPTURE_TIPPING_POINT


class TestAgentProfile:
    """Test Story 2: AgentProfile model."""
    
    def test_profile_creation(self):
        """Test basic profile creation."""
        profile = AgentProfile(
            agent_id="test_company",
            name="Test Company",
            agent_type=AgentType.company,
            description="A test company",
            objectives=["Maximize profit"],
            constraints=["Budget limited"],
            data={"revenue_usd_bn": 10.0},
            country="IN"
        )
        assert profile.agent_id == "test_company"
        assert profile.agent_type == AgentType.company
        assert profile.information_completeness == 1.0  # default
    
    def test_profile_immutable(self):
        """Test that AgentProfile is frozen."""
        profile = AgentProfile(
            agent_id="test",
            name="Test",
            agent_type=AgentType.company,
            description="Test",
            objectives=[],
            constraints=[],
            data={},
            country="IN"
        )
        with pytest.raises(Exception):  # Pydantic raises ValidationError
            profile.agent_id = "modified"
    
    def test_profile_from_json(self):
        """Test loading profile from JSON file."""
        profile_data = {
            "agent_id": "tata_steel",
            "name": "Tata Steel",
            "agent_type": "company",
            "description": "Indian steel giant",
            "objectives": ["Maximize shareholder value"],
            "constraints": ["Board approval required for capex > $1Bn"],
            "data": {"revenue_usd_bn": 22.0, "financial_health": 0.82},
            "country": "IN",
            "information_completeness": 0.95
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(profile_data, f)
            temp_path = f.name
        
        try:
            profile = AgentProfile.from_json(temp_path)
            assert profile.agent_id == "tata_steel"
            assert profile.agent_type == AgentType.company
            assert profile.data["revenue_usd_bn"] == 22.0
        finally:
            Path(temp_path).unlink()


class TestAgentState:
    """Test Story 2: AgentState model."""
    
    def test_initial_state(self):
        """Test creating initial state from profile."""
        profile = AgentProfile(
            agent_id="test",
            name="Test",
            agent_type=AgentType.company,
            description="Test",
            objectives=[],
            constraints=[],
            data={"financial_health": 0.8, "fear_greed_index": 6.0},
            country="IN"
        )
        
        state = AgentState.initial(profile)
        assert state.agent_id == "test"
        assert state.current_round == 0
        assert state.financial_health == 0.8
        assert state.fear_greed_index == 6.0
        assert state.capture_score == 0.0
    
    def test_apply_updates(self):
        """Test applying partial updates to state."""
        state = AgentState(agent_id="test", current_round=0)
        
        patch = {
            "current_round": 1,
            "fear_greed_index": 7.5,
            "metrics": {"revenue_change_pct": 5.0}
        }
        state.apply_updates(patch)
        
        assert state.current_round == 1
        assert state.fear_greed_index == 7.5
        assert state.metrics["revenue_change_pct"] == 5.0


class TestRoundResponse:
    """Test Story 3: RoundResponse model."""
    
    def test_response_creation(self):
        """Test creating a valid round response."""
        signal = PublicSignal(
            from_agent="test",
            to_agent=None,
            content="Announcing export diversion",
            signal_type="announcement",
            round=1
        )
        
        response = RoundResponse(
            agent_id="test",
            round=1,
            primary_action="export_diversion",
            assessment="Diverting exports to EU markets",
            confidence=0.75,
            impact_areas=["trade", "pricing"],
            signals_to_ecosystem=[signal]
        )
        
        assert response.agent_id == "test"
        assert response.confidence == 0.75
        assert response.is_fallback is False
        assert len(response.signals_to_ecosystem) == 1
    
    def test_fallback_response(self):
        """Test fallback response creation."""
        fallback = RoundResponse.fallback("test_agent", round=2)
        
        assert fallback.agent_id == "test_agent"
        assert fallback.round == 2
        assert fallback.is_fallback is True
        assert fallback.confidence == 0.3
        assert "FALLBACK" in fallback.assessment
        assert fallback.primary_action == "wait_and_observe"


class TestShockScenario:
    """Test Story 5: ShockScenario model."""
    
    def test_scenario_creation(self):
        """Test basic scenario creation."""
        scenario = ShockScenario(
            id="test_shock",
            name="Test Shock",
            description="A test scenario",
            category="tariff",
            severity=0.85,
            affected_sectors=["steel"],
            context="US imposed 50% tariff on steel."
        )
        
        assert scenario.severity == 0.85
        assert scenario.category == "tariff"
    
    def test_severity_validation(self):
        """Test that severity outside [0, 1] raises error."""
        with pytest.raises(ValueError, match="severity must be between"):
            ShockScenario(
                id="test",
                name="Test",
                description="Test",
                category="tariff",
                severity=1.5,  # Invalid
                affected_sectors=["steel"],
                context="Test"
            )
    
    def test_scenario_from_json(self):
        """Test loading scenario from JSON."""
        scenario_data = {
            "id": "tariff_shock",
            "name": "US Steel Tariff",
            "description": "50% tariff on Indian steel",
            "category": "tariff",
            "severity": 0.85,
            "affected_sectors": ["steel", "manufacturing"],
            "context": "The US imposed a 50% tariff.",
            "initial_market_impacts": {"steel_hrc": 0.72},
            "initiating_country": "US"
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(scenario_data, f)
            temp_path = f.name
        
        try:
            scenario = ShockScenario.from_json(temp_path)
            assert scenario.severity == 0.85
            assert scenario.initial_market_impacts["steel_hrc"] == 0.72
        finally:
            Path(temp_path).unlink()


class TestWorldState:
    """Test Story 4: WorldState and related models."""
    
    def test_world_state_creation(self):
        """Test creating world state."""
        profile = AgentProfile(
            agent_id="test",
            name="Test",
            agent_type=AgentType.company,
            description="Test",
            objectives=[],
            constraints=[],
            data={},
            country="IN"
        )
        state = AgentState.initial(profile)
        
        world = WorldState(
            current_round=0,
            scenario_name="Test Scenario",
            agent_profiles={"test": profile},
            agent_states={"test": state},
            market_states={},
            trade_routes=[],
            all_signals=[],
            events=[]
        )
        
        assert world.current_round == 0
        assert "test" in world.agent_profiles
    
    def test_get_signals_for_round(self):
        """Test filtering signals by round."""
        signal1 = PublicSignal(from_agent="a1", content="R1", signal_type="announcement", round=1)
        signal2 = PublicSignal(from_agent="a2", content="R2", signal_type="announcement", round=2)
        signal3 = PublicSignal(from_agent="a3", content="R1b", signal_type="policy", round=1)
        
        world = WorldState(
            current_round=2,
            scenario_name="Test",
            agent_profiles={},
            agent_states={},
            market_states={},
            trade_routes=[],
            all_signals=[signal1, signal2, signal3],
            events=[]
        )
        
        round1_signals = world.get_signals_for_round(1)
        assert len(round1_signals) == 2
        assert all(s.round == 1 for s in round1_signals)
    
    def test_get_responses_for_round(self):
        """Test retrieving responses for a round."""
        response1 = RoundResponse(
            agent_id="a1",
            round=1,
            primary_action="export_diversion",
            assessment="Test",
            confidence=0.7,
            impact_areas=[]
        )
        
        world = WorldState(
            current_round=1,
            scenario_name="Test",
            agent_profiles={},
            agent_states={},
            market_states={},
            trade_routes=[],
            all_signals=[],
            events=[],
            round_responses={1: {"a1": response1}}
        )
        
        responses = world.get_responses_for_round(1)
        assert len(responses) == 1
        assert "a1" in responses


class TestMarketModels:
    """Test Story 4: Market models."""
    
    def test_market_state_creation(self):
        """Test creating market state."""
        market = MarketState(
            commodity="steel_hrc",
            spot_price=650.0,
            prev_price=700.0,
            price_change_pct=-7.14,
            demand=1000.0,
            supply=900.0,
            volume_cleared=900.0,
            unmet_demand=100.0,
            unmet_demand_pct=10.0
        )
        
        assert market.commodity == "steel_hrc"
        assert market.unmet_demand_pct == 10.0
    
    def test_trade_route_creation(self):
        """Test creating trade route."""
        route = TradeRoute(
            from_country="IN",
            to_country="US",
            commodity="steel",
            volume=2100000.0,
            tariff_rate=25.0,
            friction=0.15
        )
        
        assert route.from_country == "IN"
        assert route.tariff_rate == 25.0


class TestEvents:
    """Test Story 4: Event models."""
    
    def test_world_event_creation(self):
        """Test creating world event."""
        event = WorldEvent(
            event_type=CAPTURE_TIPPING_POINT,
            round=3,
            description="DGTR captured by lobbying pressure",
            affected_agents=["dgtr", "tata_steel"],
            data={"capture_score": 0.75}
        )
        
        assert event.event_type == CAPTURE_TIPPING_POINT
        assert event.round == 3
        assert len(event.affected_agents) == 2
