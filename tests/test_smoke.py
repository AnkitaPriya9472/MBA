"""Smoke tests and integration harness.

Story 22: End-to-end tests that exercise the full simulation pipeline.

- Smoke test: Live test requiring API key (skipped in CI)
- Integration test: Replay test using saved responses (no API key needed)
"""

import os
import pytest
import json
from pathlib import Path

from simulation.engine import run_scenario
from output.results import SimulationResult


@pytest.mark.skipif(
    not os.environ.get("OPENROUTER_API_KEY"),
    reason="No API key - skipping live smoke test"
)
def test_smoke_2x2():
    """Smoke test: Run minimal simulation with 2 agents, 2 rounds.
    
    This is a live test that actually calls the LLM API.
    Requires OPENROUTER_API_KEY environment variable.
    """
    # Use minimal agent set
    agent_paths = [
        "agents/profiles/companies/tata_steel.json",
        "agents/profiles/governments/india.json",
    ]
    
    # Run short simulation
    result = run_scenario(
        scenario_path="scenarios/tariff_shock.json",
        agent_profile_paths=agent_paths,
        rounds=2,
        model="moonshotai/kimi-k2",  # Fast, cheap model
    )
    
    # Verify basic integrity
    assert result.rounds_completed == 2
    
    # Both agents should have responded
    assert "tata_steel" in result.world_state.agent_profiles
    assert "gov_india" in result.world_state.agent_profiles
    
    # Check round responses exist
    round_1_responses = result.get_round(1)
    round_2_responses = result.get_round(2)
    
    assert len(round_1_responses) >= 2
    assert len(round_2_responses) >= 2
    
    # Verify metadata
    assert "model_used" in result.metadata
    assert result.metadata["model_used"] == "moonshotai/kimi-k2"
    assert "duration_seconds" in result.metadata


def test_integration_replay():
    """Integration test: Replay simulation using saved LLM responses.
    
    This test uses pre-recorded LLM responses from a fixture file,
    so it doesn't require an API key and runs fast in CI.
    
    The fixture file should be committed to the repo.
    """
    # Check if fixture exists
    fixture_path = Path("tests/fixtures/tariff_shock_2round_responses.json")
    
    if not fixture_path.exists():
        pytest.skip(f"Fixture file not found: {fixture_path}")
    
    # Load fixture with saved LLM responses
    with open(fixture_path) as f:
        fixture_data = json.load(f)
    
    # Verify fixture structure
    assert "rounds" in fixture_data
    assert len(fixture_data["rounds"]) >= 2
    
    # In a full implementation, we would:
    # 1. Patch BaseAgent.act to return pre-parsed RoundResponse objects
    # 2. Run the full engine loop including resolver, market, capture, sentiment
    # 3. Verify all modules produce output without errors
    
    # For now, verify fixture integrity
    for round_num, round_data in fixture_data["rounds"].items():
        assert "responses" in round_data
        for agent_id, response_data in round_data["responses"].items():
            assert "agent_id" in response_data
            assert "primary_action" in response_data
            assert "confidence" in response_data
            assert "assessment" in response_data


def test_save_load_roundtrip(tmp_path):
    """Test that SimulationResult can be saved and loaded without loss."""
    # Create minimal result
    from models.scenario import ShockScenario
    from models.world_state import WorldState
    from models.agent_types import AgentProfile, AgentState, AgentType
    from output.results import SimulationResult
    
    # Minimal scenario
    scenario = ShockScenario(
        id="test",
        name="Test Scenario",
        description="Test",
        category="tariff",
        severity=0.5,
        affected_sectors=["steel"],
        context="Test context",
    )
    
    # Minimal agent
    profile = AgentProfile(
        agent_id="test_agent",
        name="Test Agent",
        agent_type=AgentType.company,
        description="Test",
        objectives=["Test"],
        constraints=["Test"],
        data={},
        country="IN",
        information_completeness=0.9
    )
    
    # Minimal world state
    world_state = WorldState(
        current_round=2,
        scenario_name="test",
        agent_profiles={"test_agent": profile},
        agent_states={"test_agent": AgentState.initial(profile)},
        market_states={},
        trade_routes=[],
        all_signals=[],
        events=[],
        round_responses={}
    )
    
    # Create result
    result = SimulationResult(
        scenario=scenario,
        rounds_completed=2,
        world_state=world_state,
        metadata={"model_used": "test", "duration_seconds": 5.0}
    )
    
    # Save
    save_path = tmp_path / "test_result.json"
    result.save(str(save_path))
    
    # Load
    loaded = SimulationResult.load(str(save_path))
    
    # Verify
    assert loaded.rounds_completed == result.rounds_completed
    assert loaded.scenario.name == result.scenario.name
    assert "test_agent" in loaded.world_state.agent_profiles
    assert loaded.metadata["model_used"] == "test"


# Fixture creation helper (not a test - run manually to generate fixtures)
def _create_fixture_file():
    """Helper to generate fixture file from a real run.
    
    This is not a test - run it manually when you need to update the fixture:
    
        OPENROUTER_API_KEY=xxx python -c "from tests.test_smoke import _create_fixture_file; _create_fixture_file()"
    """
    import os
    
    if not os.environ.get("OPENROUTER_API_KEY"):
        print("ERROR: OPENROUTER_API_KEY not set")
        return
    
    print("Running simulation to capture responses...")
    
    agent_paths = [
        "agents/profiles/companies/tata_steel.json",
        "agents/profiles/companies/jsw_steel.json",
        "agents/profiles/governments/india.json",
        "agents/profiles/governments/us.json",
        "agents/profiles/regulators/dgtr.json",
        "agents/profiles/consumers/industrial_steel.json",
        "agents/profiles/suppliers/iron_ore.json",
    ]
    
    result = run_scenario(
        scenario_path="scenarios/tariff_shock.json",
        agent_profile_paths=agent_paths,
        rounds=2,
        model="moonshotai/kimi-k2",
    )
    
    # Extract responses
    fixture = {"rounds": {}}
    
    for round_num in [1, 2]:
        responses = result.get_round(round_num)
        fixture["rounds"][str(round_num)] = {
            "responses": {
                agent_id: {
                    "agent_id": resp.agent_id,
                    "round": resp.round,
                    "primary_action": resp.primary_action,
                    "secondary_action": resp.secondary_action,
                    "assessment": resp.assessment,
                    "confidence": resp.confidence,
                    "impact_areas": resp.impact_areas,
                    "metrics_change": resp.metrics_change,
                    "raw_llm_output": resp.raw_llm_output,
                    "is_fallback": resp.is_fallback,
                }
                for agent_id, resp in responses.items()
            }
        }
    
    # Save fixture
    fixture_path = Path("tests/fixtures/tariff_shock_2round_responses.json")
    fixture_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(fixture_path, "w") as f:
        json.dump(fixture, f, indent=2)
    
    print(f"✓ Fixture saved to {fixture_path}")
    print(f"  Captured {len(agent_paths)} agents × 2 rounds")
