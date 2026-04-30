"""Simulation engine - top-level orchestrator for multi-round simulations.

Story 18: SimulationEngine and run_scenario() - the complete integration point.
"""

import json
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from pathlib import Path
from datetime import datetime

from pydantic import BaseModel
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from models.scenario import ShockScenario
from models.agent_types import AgentProfile, AgentState, RoundResponse, PublicSignal
from models.world_state import WorldState, RoundContext
from models.market import MarketState, TradeRoute
from models.events import WorldEvent
from agents.base import BaseAgent
from agents.visibility import VisibilityFilter
from agents.prompts import PromptBuilder
from simulation.market import MarketClearing
from simulation.capture import CaptureEngine
from simulation.trade import TradeNetwork
from simulation.sentiment import SentimentEngine
from simulation.resolver import StateResolver

logger = logging.getLogger(__name__)
console = Console()


class SimulationResult(BaseModel):
    """Complete results from a simulation run."""
    scenario: ShockScenario
    rounds_completed: int
    world_state: WorldState
    metadata: dict  # model_used, duration_seconds, timestamp, total_fallbacks
    
    def get_round(self, n: int) -> dict[str, RoundResponse]:
        """Get all agent responses for round n."""
        return self.world_state.round_responses.get(n, {})
    
    def get_agent_history(self, agent_id: str) -> list[RoundResponse]:
        """Get all responses from an agent across all rounds."""
        history = []
        for round_responses in self.world_state.round_responses.values():
            if agent_id in round_responses:
                history.append(round_responses[agent_id])
        return history
    
    def get_events(self, event_type: str | None = None) -> list[WorldEvent]:
        """Get events, optionally filtered by type."""
        if event_type is None:
            return self.world_state.events
        return [e for e in self.world_state.events if e.event_type == event_type]
    
    def get_capture_timeline(self) -> dict[str, list[float]]:
        """Get capture score progression per regulator."""
        timeline = {}
        for agent_id, state in self.world_state.agent_states.items():
            if state.capture_score > 0:
                # Would need to track history - simplified for now
                timeline[agent_id] = [state.capture_score]
        return timeline
    
    def get_price_timeline(self, commodity: str) -> list[float]:
        """Get price history for a commodity."""
        if commodity in self.world_state.market_states:
            return self.world_state.market_states[commodity].price_history
        return []
    
    def get_trade_flow_evolution(self) -> dict[str, list[float]]:
        """Get trade flow volume evolution per route."""
        # Would need to track route history - simplified for now
        evolution = {}
        for route in self.world_state.trade_routes:
            key = f"{route.from_country}→{route.to_country}:{route.commodity}"
            evolution[key] = [route.volume]
        return evolution
    
    def save(self, path: str) -> None:
        """Save results to JSON file."""
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to dict
        data = self.model_dump(mode="json")
        
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Saved simulation results to {path}")
    
    @classmethod
    def load(cls, path: str) -> "SimulationResult":
        """Load results from JSON file."""
        with open(path, "r") as f:
            data = json.load(f)
        return cls.model_validate(data)


class SimulationEngine:
    """Top-level orchestrator for multi-round multi-agent simulations.
    
    The 4-phase round loop:
    1. Build RoundContext per agent (visibility filtering + capture bias)
    2. Execute all agents in parallel
    3. StateResolver.resolve() → RoundResolution  
    4. Apply patches to AgentStates, update WorldState, print summary
    """
    
    AGENT_TIMEOUT_SECONDS = 30
    MAX_PARALLEL_WORKERS = 8

    def __init__(
        self,
        scenario: ShockScenario,
        agents: list[BaseAgent],
        trade_network: TradeNetwork,
        market: MarketClearing,
        capture: CaptureEngine,
        sentiment: SentimentEngine,
    ):
        self.scenario = scenario
        self.agents = agents
        self.trade_network = trade_network
        self.market = market
        self.capture = capture
        self.sentiment = sentiment
        
        # Initialize WorldState
        self.world_state = WorldState(
            current_round=0,
            scenario_name=scenario.name,
            agent_profiles={a.agent_id: a.profile for a in agents},
            agent_states={a.agent_id: a.state for a in agents},
            market_states={},  # Will be initialized in run()
            trade_routes=trade_network.routes,
            all_signals=[],
            events=[],
            round_responses={},
        )
        
        # Initialize resolver
        self.resolver = StateResolver(market, capture, trade_network, sentiment)
        
        # Initialize sub-components
        self.visibility_filter = VisibilityFilter()
        self.prompt_builder = PromptBuilder()
        
        # Tracking
        self.total_api_calls = 0
        self.total_fallbacks = 0

    def run(self, rounds: int = 5) -> SimulationResult:
        """Run the simulation for N rounds.
        
        Returns:
            SimulationResult with complete world state and metadata
        """
        start_time = time.time()
        
        # Print scenario header
        console.print(Panel(
            f"[bold cyan]{self.scenario.name}[/bold cyan]\n\n"
            f"{self.scenario.description}\n\n"
            f"[bold]Category:[/bold] {self.scenario.category}\n"
            f"[bold]Severity:[/bold] {self.scenario.severity}\n"
            f"[bold]Agents:[/bold] {len(self.agents)}\n"
            f"[bold]Rounds:[/bold] {rounds}",
            title="SIMULATION START",
            border_style="cyan",
            box=box.DOUBLE,
        ))
        
        # Apply initial market impacts from scenario
        self._apply_initial_market_impacts()
        
        # Main round loop
        for round_num in range(1, rounds + 1):
            logger.info(f"\n{'='*60}\nROUND {round_num} OF {rounds}\n{'='*60}")
            console.print(f"\n[bold magenta]{'━' * 60}[/bold magenta]")
            console.print(f"[bold magenta]  ROUND {round_num} OF {rounds}[/bold magenta]")
            console.print(f"[bold magenta]{'━' * 60}[/bold magenta]\n")
            
            self.world_state.current_round = round_num
            
            # Phase 1: Build RoundContext per agent
            contexts = self._phase1_build_contexts(round_num)
            
            # Phase 2: Execute agents in parallel
            responses = self._phase2_execute_agents(contexts)
            
            # Phase 3: Resolve round
            resolution = self._phase3_resolve(responses)
            
            # Phase 4: Apply updates and print summary
            self._phase4_apply_updates(resolution, responses)
            
            # Print round summary
            self._print_round_summary(round_num, responses, resolution)
            
            # Check for convergence (all agents waiting)
            if self._check_convergence(responses, round_num):
                logger.info(f"Convergence detected at round {round_num}")
                console.print(f"\n[yellow]⚠ Convergence detected - all agents waiting[/yellow]\n")
                break
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Build result
        result = SimulationResult(
            scenario=self.scenario,
            rounds_completed=self.world_state.current_round,
            world_state=self.world_state,
            metadata={
                "model_used": self.agents[0].model if self.agents else "unknown",
                "duration_seconds": duration,
                "timestamp": datetime.now().isoformat(),
                "total_api_calls": self.total_api_calls,
                "total_fallbacks": self.total_fallbacks,
            },
        )
        
        console.print(Panel(
            f"[bold green]Simulation Complete[/bold green]\n\n"
            f"Rounds: {result.rounds_completed}\n"
            f"Duration: {duration:.1f}s\n"
            f"Total API calls: {self.total_api_calls}\n"
            f"Fallbacks: {self.total_fallbacks}\n"
            f"Events fired: {len(self.world_state.events)}",
            title="SIMULATION END",
            border_style="green",
            box=box.DOUBLE,
        ))
        
        return result

    def _apply_initial_market_impacts(self) -> None:
        """Apply scenario's initial market impacts to round 1 prices."""
        for commodity, multiplier in self.scenario.initial_market_impacts.items():
            # Create initial market state
            baseline_price = 500.0  # Default baseline
            initial_price = baseline_price * multiplier
            
            self.world_state.market_states[commodity] = MarketState(
                commodity=commodity,
                spot_price=initial_price,
                prev_price=None,
                price_change_pct=None,
                demand=0.0,
                supply=0.0,
                volume_cleared=0.0,
                unmet_demand=0.0,
                unmet_demand_pct=0.0,
                price_history=[initial_price],
            )

    def _phase1_build_contexts(self, round_num: int) -> dict[str, RoundContext]:
        """Phase 1: Build RoundContext for each agent."""
        contexts = {}
        
        for agent in self.agents:
            # Get visible signals
            visible_signals = self.visibility_filter.get_visible_signals(
                self.world_state, agent.profile, round_num
            )
            
            # Get competitive effects
            competitive_effects = self.visibility_filter.get_competitive_effects(
                self.world_state, agent.profile
            )
            
            # Get capture bias if applicable
            capture_bias = None
            if agent.profile.agent_type == "regulator":
                capture_bias = self.capture.get_bias_prompt(agent.agent_id)
            
            context = RoundContext(
                agent_id=agent.agent_id,
                round=round_num,
                shock={
                    "name": self.scenario.name,
                    "context": self.scenario.context,
                    "severity": self.scenario.severity,
                },
                visible_signals=visible_signals,
                market_state=self.world_state.market_states,
                competitive_effects=competitive_effects,
                impacts_on_agent={},  # Would compute scenario-specific impacts
                own_state=agent.state,
                capture_bias=capture_bias,
            )
            
            contexts[agent.agent_id] = context
        
        return contexts

    def _phase2_execute_agents(
        self,
        contexts: dict[str, RoundContext],
    ) -> dict[str, RoundResponse]:
        """Phase 2: Execute all agents in parallel."""
        responses = {}
        num_workers = min(len(self.agents), self.MAX_PARALLEL_WORKERS)
        
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            # Submit all agent tasks
            future_to_agent = {
                executor.submit(agent.act, contexts[agent.agent_id]): agent
                for agent in self.agents
            }
            
            # Collect results
            for future in as_completed(future_to_agent):
                agent = future_to_agent[future]
                try:
                    response = future.result(timeout=self.AGENT_TIMEOUT_SECONDS)
                    responses[agent.agent_id] = response
                    self.total_api_calls += 1
                    
                    if response.is_fallback:
                        self.total_fallbacks += 1
                        logger.warning(f"Fallback used for {agent.agent_id}")
                    
                except TimeoutError:
                    logger.error(f"Timeout for {agent.agent_id}")
                    fallback = RoundResponse.fallback(
                        agent.agent_id, contexts[agent.agent_id].round
                    )
                    responses[agent.agent_id] = fallback
                    self.total_fallbacks += 1
                    
                except Exception as e:
                    logger.error(f"Error executing {agent.agent_id}: {e}", exc_info=True)
                    fallback = RoundResponse.fallback(
                        agent.agent_id, contexts[agent.agent_id].round
                    )
                    responses[agent.agent_id] = fallback
                    self.total_fallbacks += 1
        
        return responses

    def _phase3_resolve(
        self,
        responses: dict[str, RoundResponse],
    ) -> "RoundResolution":
        """Phase 3: Run StateResolver."""
        profiles = {a.agent_id: a.profile for a in self.agents}
        return self.resolver.resolve(responses, self.world_state, profiles)

    def _phase4_apply_updates(
        self,
        resolution: "RoundResolution",
        responses: dict[str, RoundResponse],
    ) -> None:
        """Phase 4: Apply resolution patches to world state."""
        # Update agent states
        for agent_id, patch in resolution.agent_state_patches.items():
            if agent_id in self.world_state.agent_states:
                self.world_state.agent_states[agent_id].apply_updates(patch)
        
        # Update market states
        self.world_state.market_states = resolution.market_clearing
        
        # Append new signals
        for response in responses.values():
            self.world_state.all_signals.extend(response.signals_to_ecosystem)
        
        # Append events
        self.world_state.events.extend(resolution.events)
        
        # Store round responses
        self.world_state.round_responses[resolution.round] = responses

    def _print_round_summary(
        self,
        round_num: int,
        responses: dict[str, RoundResponse],
        resolution: "RoundResolution",
    ) -> None:
        """Print formatted round summary table."""
        table = Table(
            title=f"Round {round_num} Summary",
            box=box.ROUNDED,
            show_lines=True,
        )
        table.add_column("Agent", style="bold cyan", width=20)
        table.add_column("Action", style="green", width=20)
        table.add_column("Confidence", style="yellow", width=10)
        table.add_column("Assessment", style="white", width=60)
        table.add_column("Sentiment", style="magenta", width=10)
        
        for agent_id, response in responses.items():
            profile = self.world_state.agent_profiles[agent_id]
            state = self.world_state.agent_states[agent_id]
            
            # Truncate assessment
            assessment = response.assessment[:77] + "..." if len(response.assessment) > 80 else response.assessment
            
            # Format sentiment
            sentiment_str = f"{state.fear_greed_index:.1f}/10"
            
            table.add_row(
                profile.name,
                response.primary_action,
                f"{response.confidence:.0%}",
                assessment,
                sentiment_str,
            )
        
        console.print(table)
        
        # Print events if any
        if resolution.events:
            console.print(f"\n[bold red]⚠ Events:[/bold red]")
            for event in resolution.events:
                console.print(f"  • [{event.event_type}] {event.description}")

    def _check_convergence(
        self,
        responses: dict[str, RoundResponse],
        round_num: int,
    ) -> bool:
        """Check if all agents are in wait/hold mode for 2+ consecutive rounds."""
        if round_num < 2:
            return False
        
        wait_actions = {
            "wait_and_observe", "do_nothing", "wait", "hold",
            "hold_prices", "hold_supply", "issue_cautionary_note"
        }
        
        # Check current round
        all_waiting_now = all(
            r.primary_action in wait_actions for r in responses.values()
        )
        
        if not all_waiting_now:
            return False
        
        # Check previous round
        prev_responses = self.world_state.round_responses.get(round_num - 1, {})
        all_waiting_prev = all(
            r.primary_action in wait_actions for r in prev_responses.values()
        )
        
        return all_waiting_prev


def run_scenario(
    scenario_path: str,
    agent_profile_paths: list[str],
    institution_paths: list[str] = [],
    network_path: str = "network/steel_ecosystem.json",
    rounds: int = 3,
    model: str = "moonshotai/kimi-k2",
) -> SimulationResult:
    """Convenience function to run a complete scenario from file paths.
    
    Args:
        scenario_path: Path to scenario JSON file
        agent_profile_paths: List of paths to agent profile JSON files
        institution_paths: Paths to institution rule files (optional)
        network_path: Path to trade network JSON
        rounds: Number of simulation rounds
        model: LLM model identifier (OpenRouter format)
        
    Returns:
        SimulationResult object
        
    Example:
        >>> result = run_scenario(
        ...     'scenarios/tariff_shock.json',
        ...     [
        ...         'agents/profiles/companies/tata_steel.json',
        ...         'agents/profiles/governments/india.json',
        ...     ],
        ...     rounds=3,
        ... )
        >>> result.save('data/runs/tariff_shock_results.json')
    """
    # Load scenario
    scenario = ShockScenario.from_json(scenario_path)
    
    # Load agent profiles and create agents
    agents = []
    for profile_path in agent_profile_paths:
        profile = AgentProfile.from_json(profile_path)
        agent = BaseAgent(profile, model=model)
        agents.append(agent)
    
    # Load trade network
    trade_network = TradeNetwork.load(network_path)
    
    # Initialize sub-engines
    market = MarketClearing()
    capture = CaptureEngine()
    sentiment = SentimentEngine()
    
    # Initialize regulators in capture engine
    for agent in agents:
        if agent.profile.agent_type == "regulator":
            vulnerability = agent.profile.data.get("capture_vulnerability", 0.5)
            capture.initialize_regulator(agent.agent_id, vulnerability)
    
    # Create engine
    engine = SimulationEngine(
        scenario=scenario,
        agents=agents,
        trade_network=trade_network,
        market=market,
        capture=capture,
        sentiment=sentiment,
    )
    
    # Run simulation
    return engine.run(rounds=rounds)

