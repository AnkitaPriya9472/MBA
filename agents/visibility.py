"""VisibilityFilter — Information asymmetry engine for agent decision-making.

This module implements Story 10 of the implementation plan:
- Filters signals based on information completeness and geographic proximity
- Enforces 1-round delay for cross-border signals
- Computes competitive effects from other agents' actions
- Ensures deterministic filtering via seeded randomness
"""

import random
from typing import Any

from models.agent_types import AgentProfile, AgentType, PublicSignal
from models.world_state import WorldState


class VisibilityFilter:
    """Implements information asymmetry across agents.
    
    Each agent sees a different filtered view of the world based on:
    - Information completeness score (0.0–1.0)
    - Geographic proximity (same-country vs cross-border)
    - Direct partnerships and government relationships
    """
    
    @staticmethod
    def get_visible_signals(
        world_state: WorldState,
        profile: AgentProfile,
        round: int
    ) -> list[PublicSignal]:
        """Filter signals visible to an agent based on information asymmetry.
        
        Rules:
        1. Private intents are NEVER included (only PublicSignals exist in world_state.all_signals)
        2. Must-keep signals (direct partners, own government) are always included
        3. Cross-country signals have 1-round delay
        4. Other signals included with probability = information_completeness
        
        Args:
            world_state: Complete simulation state
            profile: Agent profile requesting visibility
            round: Current round number
        
        Returns:
            List of PublicSignals visible to this agent
        """
        current_round = round
        agent_country = profile.country
        agent_profile = world_state.agent_profiles.get(profile.agent_id)
        
        # Initialize deterministic RNG for reproducibility
        rng = random.Random(round * 1000 + hash(profile.agent_id) % 1000)
        
        visible = []
        
        for signal in world_state.all_signals:
            # Skip signals from future rounds (shouldn't happen but defensive)
            if signal.round > current_round:
                continue
            
            # Skip own signals (agent has them in memory already)
            if signal.from_agent == profile.agent_id:
                continue
            
            # Get sender's profile for country check
            sender_profile = world_state.agent_profiles.get(signal.from_agent)
            if not sender_profile:
                continue
            
            sender_country = sender_profile.country
            
            # Check if this is a must-keep signal
            is_must_keep = VisibilityFilter._is_must_keep_signal(
                signal, profile, sender_profile, world_state
            )
            
            # Apply information delay rule for cross-country signals
            if sender_country != agent_country:
                # Cross-country signals have 1-round delay
                if signal.round > current_round - 2:
                    # Signal too recent (produced last round or this round)
                    if not is_must_keep:
                        continue  # Skip unless it's must-keep
            else:
                # Same-country signals visible from previous round
                if signal.round > current_round - 1:
                    if not is_must_keep:
                        continue
            
            # Must-keep signals always included
            if is_must_keep:
                visible.append(signal)
                continue
            
            # Other signals included with probability = information_completeness
            if rng.random() < profile.information_completeness:
                visible.append(signal)
        
        return visible
    
    @staticmethod
    def _is_must_keep_signal(
        signal: PublicSignal,
        profile: AgentProfile,
        sender_profile: AgentProfile,
        world_state: WorldState
    ) -> bool:
        """Check if a signal must be kept regardless of information completeness.
        
        Must-keep rules:
        - Government agents: all signals from own-country agents
        - Company agents: signals from home_government_id and direct_partners
        - Regulator agents: signals from own-jurisdiction government
        """
        # Government agents see all own-country signals
        if profile.agent_type == AgentType.government:
            if sender_profile.country == profile.country:
                return True
        
        # Company/consumer/supplier agents see signals from their home government
        if profile.agent_type in [AgentType.company, AgentType.consumer, AgentType.supplier]:
            if profile.home_government_id and signal.from_agent == profile.home_government_id:
                return True
        
        # All agents see signals from direct partners
        if signal.from_agent in profile.direct_partners:
            return True
        
        # Regulator agents see signals from own-jurisdiction government
        if profile.agent_type == AgentType.regulator:
            # Find government in same country
            for agent_id, agent_prof in world_state.agent_profiles.items():
                if (agent_prof.agent_type == AgentType.government and
                    agent_prof.country == profile.country and
                    signal.from_agent == agent_id):
                    return True
        
        return False
    
    @staticmethod
    def get_competitive_effects(
        world_state: WorldState,
        profile: AgentProfile
    ) -> dict[str, float]:
        """Compute competitive effects from other agents' recent actions.
        
        Analyzes the previous round's responses and returns rule-based effects:
        - Competitor export diversion to same markets
        - Government subsidies to competitors
        - Investor sell pressure
        
        Args:
            world_state: Complete simulation state
            profile: Agent profile requesting competitive effects
        
        Returns:
            Dict of effect_name → magnitude (0.0–1.0)
        """
        effects: dict[str, float] = {}
        
        current_round = world_state.current_round
        if current_round == 0:
            return effects  # No prior round to analyze
        
        # Get last round's responses
        last_round_responses = world_state.get_responses_for_round(current_round - 1)
        
        # Only relevant for company agents
        if profile.agent_type == AgentType.company:
            # Check for competitor export diversion
            for agent_id, response in last_round_responses.items():
                if agent_id == profile.agent_id:
                    continue  # Skip own response
                
                responder_profile = world_state.agent_profiles.get(agent_id)
                if not responder_profile:
                    continue
                
                # Check if competitor company diverted exports
                if responder_profile.agent_type == AgentType.company:
                    if response.primary_action == "export_diversion":
                        # Competitor is diverting exports - creates market pressure
                        effects["competitor_diversion_pressure"] = 0.3
                
                # Check if government issued subsidy to competitor
                if responder_profile.agent_type == AgentType.government:
                    if response.primary_action == "subsidy":
                        # Government subsidizing competitors hurts this company
                        effects["competitor_subsidy_advantage"] = 0.2
                
                # Check if investors are selling this company
                if responder_profile.agent_type == AgentType.investor:
                    if response.primary_action in ["sell", "short"]:
                        # Investor sentiment is negative
                        effects["investor_sell_pressure"] = 0.4
        
        return effects
