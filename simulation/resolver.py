"""State resolver - 10-step resolution pipeline.

Story 17: StateResolver - deterministic brain that takes all agent responses
and produces a RoundResolution. Order of steps is load-bearing.
"""

import logging
from typing import Any
from pydantic import BaseModel

from models.agent_types import AgentProfile, RoundResponse, AgentState
from models.world_state import WorldState, RoundResolution
from models.market import MarketState, TradeRoute
from models.events import WorldEvent
from simulation.market import MarketClearing, SupplyOffer, DemandRequest
from simulation.capture import CaptureEngine, LobbyingAction
from simulation.trade import TradeNetwork
from simulation.sentiment import (
    SentimentEngine, AgentOutcome, PeerBehaviorSummary,
    AGGRESSIVE_ACTIONS, DEFENSIVE_ACTIONS
)

logger = logging.getLogger(__name__)


class StateResolver:
    """Deterministic 10-step resolution pipeline.
    
    Takes all agent responses for a round and produces:
    - Updated market states
    - Trade flow changes
    - Capture score updates
    - Sentiment updates
    - Valuation changes
    - Conflicts
    - Events
    - Per-agent state patches
    
    Order of execution is critical and must not be changed.
    """

    def __init__(
        self,
        market: MarketClearing,
        capture: CaptureEngine,
        trade: TradeNetwork,
        sentiment: SentimentEngine,
    ):
        self.market = market
        self.capture = capture
        self.trade = trade
        self.sentiment = sentiment

    def resolve(
        self,
        responses: dict[str, RoundResponse],
        world_state: WorldState,
        profiles: dict[str, AgentProfile],
    ) -> RoundResolution:
        """Execute 10-step resolution pipeline.
        
        Args:
            responses: agent_id -> RoundResponse for this round
            world_state: Current world state (market prices, agent states, etc.)
            profiles: agent_id -> AgentProfile
            
        Returns:
            RoundResolution with all computed changes
        """
        round_number = world_state.current_round
        
        logger.info(f"=== Starting Resolution for Round {round_number} ===")
        
        # Initialize resolution object
        resolution = RoundResolution(
            round=round_number,
            trade_flow_changes=[],
            market_clearing={},
            capture_updates={},
            valuation_changes={},
            sentiment_updates={},
            conflicts=[],
            agent_state_patches={},
            events=[],
        )
        
        try:
            # ===== STEP 1: Extract and apply policy changes =====
            logger.info("Step 1: Extracting policy changes")
            self._step1_apply_policies(responses, world_state)
            
            # ===== STEP 2: Recalculate trade flows =====
            logger.info("Step 2: Recalculating trade flows")
            resolution.trade_flow_changes = self._step2_recalculate_trade(world_state)
            
            # ===== STEP 3: Market clearing =====
            logger.info("Step 3: Running market clearing")
            resolution.market_clearing = self._step3_market_clearing(
                responses, world_state, profiles
            )
            
            # ===== STEP 4: Capture updates =====
            logger.info("Step 4: Processing lobbying and capture")
            capture_states, capture_events = self._step4_capture_updates(
                responses, round_number
            )
            resolution.capture_updates = {
                rid: state.capture_score for rid, state in capture_states.items()
            }
            resolution.events.extend(capture_events)
            
            # ===== STEP 5: Investor valuation changes =====
            logger.info("Step 5: Computing valuation changes")
            resolution.valuation_changes = self._step5_valuation_changes(responses)
            
            # ===== STEP 6: Conflict detection =====
            logger.info("Step 6: Detecting conflicts")
            resolution.conflicts = self._step6_detect_conflicts(responses, profiles)
            
            # ===== STEP 7: Competitive effects =====
            logger.info("Step 7: Computing competitive effects")
            competitive_effects = self._step7_competitive_effects(
                responses, profiles, resolution.market_clearing
            )
            
            # ===== STEP 8: Sentiment updates =====
            logger.info("Step 8: Updating sentiment")
            resolution.sentiment_updates = self._step8_sentiment_updates(
                responses, world_state, profiles, resolution.market_clearing,
                resolution.conflicts
            )
            
            # ===== STEP 9: Assemble per-agent state patches =====
            logger.info("Step 9: Assembling state patches")
            resolution.agent_state_patches = self._step9_assemble_patches(
                responses,
                resolution.market_clearing,
                resolution.capture_updates,
                resolution.sentiment_updates,
                resolution.valuation_changes,
                competitive_effects,
                world_state,
                profiles,
            )
            
            # ===== STEP 10: Collect events =====
            logger.info("Step 10: Collecting events")
            trade_events = self.trade.detect_events(round_number)
            resolution.events.extend(trade_events)
            
            # Add custom threshold events
            threshold_events = self._step10_threshold_events(
                resolution, world_state, round_number
            )
            resolution.events.extend(threshold_events)
            
            logger.info(f"=== Resolution Complete for Round {round_number} ===")
            logger.info(f"  - Conflicts: {len(resolution.conflicts)}")
            logger.info(f"  - Events: {len(resolution.events)}")
            logger.info(f"  - Agents updated: {len(resolution.agent_state_patches)}")
            
            return resolution
            
        except Exception as e:
            logger.error(f"Resolution failed at round {round_number}: {e}", exc_info=True)
            raise

    def _step1_apply_policies(
        self,
        responses: dict[str, RoundResponse],
        world_state: WorldState,
    ) -> None:
        """Step 1: Extract government policy actions and apply to trade network."""
        for agent_id, response in responses.items():
            profile = world_state.agent_profiles.get(agent_id)
            if not profile or profile.agent_type != "government":
                continue
            
             # Extract policy details from response
            # In full implementation, would parse from response.metrics_change
            # or additional fields. For now, simplified extraction.
            action = response.primary_action
            
            if action == "retaliatory_tariff":
                # Example: India retaliates against US
                # Would need target_country from response
                target = "US"  # Placeholder - should come from response data
                magnitude = 25.0  # Would come from response
                self.trade.apply_policy(
                    action="retaliatory_tariff",
                    actor_country=profile.country,
                    target_country=target,
                    commodity="all",
                    magnitude=magnitude,
                )
                
            elif action == "subsidy":
                magnitude = 10.0  # Would extract from response
                self.trade.apply_policy(
                    action="subsidy",
                    actor_country=profile.country,
                    target_country="",  # Not applicable for subsidies
                    commodity="steel_hrc",
                    magnitude=magnitude,
                )

    def _step2_recalculate_trade(self, world_state: WorldState) -> list[TradeRoute]:
        """Step 2: Recalculate trade flows based on updated policies."""
        return self.trade.recalculate_flows(world_state.market_states)

    def _step3_market_clearing(
        self,
        responses: dict[str, RoundResponse],
        world_state: WorldState,
        profiles: dict[str, AgentProfile],
    ) -> dict[str, MarketState]:
        """Step 3: Run market clearing with supply/demand from agents."""
        supply_offers: list[SupplyOffer] = []
        demand_requests: list[DemandRequest] = []
        
        for agent_id, response in responses.items():
            profile = profiles.get(agent_id)
            if not profile:
                continue
            
            # Extract supply offers from suppliers and companies
            if profile.agent_type in ("supplier", "company"):
                # Would extract from response.metrics_change or additional fields
                # Simplified for now
                if "volume_offered_mt" in response.metrics_change:
                    supply_offers.append(SupplyOffer(
                        agent_id=agent_id,
                        product="steel_hrc",  # Would detect from profile
                        volume_mt=response.metrics_change["volume_offered_mt"],
                        min_price_usd_per_mt=response.metrics_change.get("min_price", 500.0),
                    ))
            
            # Extract demand from consumers and companies
            if profile.agent_type in ("consumer", "company"):
                if "volume_demand_mt" in response.metrics_change:
                    demand_requests.append(DemandRequest(
                        agent_id=agent_id,
                        product="steel_hrc",
                        volume_mt=response.metrics_change["volume_demand_mt"],
                        max_price_usd_per_mt=response.metrics_change.get("max_price", 800.0),
                    ))
        
        # Apply government stimulus effects (+10% demand)
        for agent_id, response in responses.items():
            profile = profiles.get(agent_id)
            if profile and profile.agent_type == "government":
                if response.primary_action == "stimulus":
                    # Boost all demand by 10%
                    for req in demand_requests:
                        req.volume_mt *= 1.10
        
        # Run market clearing
        prev_states = world_state.market_states
        return self.market.clear_all_products(
            all_offers=supply_offers,
            all_requests=demand_requests,
            round_number=world_state.current_round,
            prev_market_states=prev_states,
        )

    def _step4_capture_updates(
        self,
        responses: dict[str, RoundResponse],
        round_number: int,
    ) -> tuple[dict[str, Any], list[WorldEvent]]:
        """Step 4: Process lobbying actions and update capture scores."""
        lobbying_actions: list[LobbyingAction] = []
        
        for agent_id, response in responses.items():
            # Extract lobbying from company responses
            if "lobby_target" in response.metrics_change:
                lobby_amount = response.metrics_change.get("lobby_amount_usd_mn", 0.0)
                if lobby_amount > 0:
                    lobbying_actions.append(LobbyingAction(
                        from_company_id=agent_id,
                        to_regulator_id=response.metrics_change["lobby_target"],
                        amount_usd_mn=lobby_amount,
                        round=round_number,
                    ))
        
        return self.capture.process_round(lobbying_actions, round_number)

    def _step5_valuation_changes(
        self,
        responses: dict[str, RoundResponse],
    ) -> dict[str, float]:
        """Step 5: Compute valuation changes from investor positions."""
        valuation_changes: dict[str, float] = {}
        
        for agent_id, response in responses.items():
            # Extract investor actions
            if "position_changes" in response.metrics_change:
                positions = response.metrics_change["position_changes"]
                for target_agent_id, amount_usd_mn in positions.items():
                    if amount_usd_mn > 0:
                        # Buy → increase valuation
                        delta = amount_usd_mn * 0.02  # 2% impact per $1M invested
                    elif amount_usd_mn < 0:
                        # Sell → decrease valuation
                        delta = amount_usd_mn * 0.02
                    else:
                        continue
                    
                    # Check if it's a short position
                    if response.primary_action == "short":
                        delta *= 2.0  # Shorts have double the impact
                    
                    valuation_changes[target_agent_id] = (
                        valuation_changes.get(target_agent_id, 0.0) + delta
                    )
        
        return valuation_changes

    def _step6_detect_conflicts(
        self,
        responses: dict[str, RoundResponse],
        profiles: dict[str, AgentProfile],
    ) -> list[dict]:
        """Step 6: Detect conflicts between agents' actions."""
        conflicts = []
        
        # Track export diversions by market
        diversions_by_market: dict[str, list[str]] = {}
        
        for agent_id, response in responses.items():
            profile = profiles.get(agent_id)
            if not profile or profile.agent_type != "company":
                continue
            
            if response.primary_action == "export_diversion":
                # Extract target markets
                target_markets = response.metrics_change.get("target_markets", [])
                for market in target_markets:
                    if market not in diversions_by_market:
                        diversions_by_market[market] = []
                    diversions_by_market[market].append(agent_id)
        
        # Detect conflicts where Multiple companies target same market
        for market, agent_ids in diversions_by_market.items():
            if len(agent_ids) > 1:
                conflicts.append({
                    "type": "export_diversion_conflict",
                    "market": market,
                    "agents": agent_ids,
                    "penalty_pct": 30.0,  # Each gets 30% volume penalty
                    "description": (
                        f"Multiple companies ({', '.join(agent_ids)}) "
                        f"simultaneously diverted exports to {market}, "
                        f"creating oversupply and pricing pressure."
                    ),
                })
        
        return conflicts

    def _step7_competitive_effects(
        self,
        responses: dict[str, RoundResponse],
        profiles: dict[str, AgentProfile],
        market_clearing: dict[str, MarketState],
    ) -> dict[str, dict[str, float]]:
        """Step 7: Compute competitive effects on each agent.
        
        Returns dict[agent_id -> dict[effect_name -> magnitude]]
        """
        effects: dict[str, dict[str, float]] = {}
        
        for agent_id in profiles:
            effects[agent_id] = {}
        
        # Detect price war effects
        for agent_id, response in responses.items():
            if response.primary_action == "price_war":
                # Identify competitors (same country, same sector)
                profile = profiles.get(agent_id)
                if not profile:
                    continue
                    
                for other_id, other_profile in profiles.items():
                    if other_id == agent_id:
                        continue
                    if (other_profile.agent_type == "company" and
                        other_profile.country == profile.country):
                        # Competitor's margin reduced by 8%
                        if other_id not in effects:
                            effects[other_id] = {}
                        effects[other_id]["price_war_pressure"] = -8.0
        
        # Detect export diversion flooding effects
        for agent_id, response in responses.items():
            if response.primary_action == "export_diversion":
                target_markets = response.metrics_change.get("target_markets", [])
                # Markets with diversion see 5% price drop
                for market in target_markets:
                    # Would need to map markets to affected agents
                    # Simplified for now
                    pass
        
        # Detect subsidy advantages
        for agent_id, response in responses.items():
            profile = profiles.get(agent_id)
            if profile and profile.agent_type == "government":
                if response.primary_action == "subsidy":
                    # Competitors of subsidized companies see disadvantage
                    # Would extract beneficiaries from response
                    pass
        
        # Detect investor sell pressure
        for agent_id, response in responses.items():
            if response.primary_action == "sell":
                positions = response.metrics_change.get("position_changes", {})
                for target_id, amount in positions.items():
                    if amount < 0:  # Selling
                        if target_id not in effects:
                            effects[target_id] = {}
                        effects[target_id]["investor_sell_pressure"] = 0.4
        
        return effects

    def _step8_sentiment_updates(
        self,
        responses: dict[str, RoundResponse],
        world_state: WorldState,
        profiles: dict[str, AgentProfile],
        market_clearing: dict[str, MarketState],
        conflicts: list[dict],
    ) -> dict[str, float]:
        """Step 8: Update fear-greed sentiment for all agents."""
        # Build peer behavior summary
        all_actions = [r.primary_action for r in responses.values()]
        aggressive_set = set()
        for agent_type, actions in AGGRESSIVE_ACTIONS.items():
            aggressive_set.update(actions)
        
        peer_summary = self.sentiment.build_peer_summary(all_actions, aggressive_set)
        
        # Build outcomes for each agent
        outcomes: list[AgentOutcome] = []
        
        for agent_id, response in responses.items():
            profile = profiles.get(agent_id)
            if not profile:
                continue
            
            state = world_state.agent_states.get(agent_id)
            if not state:
                continue
            
            # Extract outcome metrics
            revenue_change_pct = response.metrics_change.get("revenue_change_pct", 0.0)
            market_share_change_pct = response.metrics_change.get("market_share_change_pct", 0.0)
            
            # Determine if action succeeded
            action_succeeded = response.confidence > 0.6  # Heuristic
            
            # Check if action conflicted
            action_conflicted = any(
                agent_id in conflict.get("agents", [])
                for conflict in conflicts
            )
            
            outcome = AgentOutcome(
                agent_id=agent_id,
                agent_type=profile.agent_type,
                revenue_change_pct=revenue_change_pct,
                market_share_change_pct=market_share_change_pct,
                action_succeeded=action_succeeded,
                action_conflicted=action_conflicted,
                loss_aversion_multiplier=profile.data.get("loss_aversion_multiplier", 2.0),
                herd_tendency=profile.data.get("herd_tendency", 0.5),
                prev_sentiment=state.fear_greed_index,
            )
            outcomes.append(outcome)
        
        return self.sentiment.compute_all(outcomes, peer_summary)

    def _step9_assemble_patches(
        self,
        responses: dict[str, RoundResponse],
        market_clearing: dict[str, MarketState],
        capture_updates: dict[str, float],
        sentiment_updates: dict[str, float],
        valuation_changes: dict[str, float],
        competitive_effects: dict[str, dict[str, float]],
        world_state: WorldState,
        profiles: dict[str, AgentProfile],
    ) -> dict[str, dict]:
        """Step 9: Assemble partial state patches for each agent.
        
        Later steps override earlier steps if they patch the same field.
        """
        patches: dict[str, dict] = {}
        
        for agent_id in profiles:
            patch = {}
            
            # Update round number
            patch["current_round"] = world_state.current_round
            
            # Update from market clearing
            # Would extract revenue, margin changes from market state
            # Simplified for now
            
            # Update capture scores
            if agent_id in capture_updates:
                patch["capture_score"] = capture_updates[agent_id]
            
            # Update sentiment
            if agent_id in sentiment_updates:
                patch["fear_greed_index"] = sentiment_updates[agent_id]
            
            # Update valuations
            if agent_id in valuation_changes:
                patch["valuation_change_pct"] = valuation_changes[agent_id]
            
            # Update from competitive effects
            if agent_id in competitive_effects:
                # Store competitive effects in metrics
                if "metrics" not in patch:
                    patch["metrics"] = {}
                patch["metrics"].update(competitive_effects[agent_id])
            
            # Record completed action
            response = responses.get(agent_id)
            if response:
                current_completed = world_state.agent_states[agent_id].completed_actions
                patch["completed_actions"] = current_completed + [response.primary_action]
            
            patches[agent_id] = patch
        
        return patches

    def _step10_threshold_events(
        self,
        resolution: RoundResolution,
        world_state: WorldState,
        round_number: int,
    ) -> list[WorldEvent]:
        """Step 10: Generate threshold-based events."""
        events = []
        
        # Check for valuation collapse
        for agent_id, change_pct in resolution.valuation_changes.items():
            if change_pct < -20.0:  # 20% drop
                events.append(WorldEvent(
                    event_type="VALUATION_COLLAPSE",
                    round=round_number,
                    description=(
                        f"{agent_id} valuation collapsed {abs(change_pct):.1f}% "
                        f"due to investor sell-off."
                    ),
                    affected_agents=[agent_id],
                    data={"valuation_change_pct": change_pct},
                ))
        
        # Check for market price shocks
        for commodity, state in resolution.market_clearing.items():
            if state.price_change_pct and abs(state.price_change_pct) > 20.0:
                events.append(WorldEvent(
                    event_type="SUPPLY_SHOCK" if state.price_change_pct > 0 else "MARKET_FLOOD",
                    round=round_number,
                    description=(
                        f"{commodity} price {'surged' if state.price_change_pct > 0 else 'crashed'} "
                        f"{abs(state.price_change_pct):.1f}% to ${state.spot_price:.2f}/MT."
                    ),
                    affected_agents=[],  # Would map to affected agents
                    data={
                        "commodity": commodity,
                        "price_change_pct": state.price_change_pct,
                        "new_price": state.spot_price,
                    },
                ))
        
        return events
