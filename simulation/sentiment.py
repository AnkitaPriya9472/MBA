"""Sentiment engine using prospect theory for fear-greed dynamics.

Story 16: SentimentEngine - updates fear-greed indices using Kahneman-Tversky prospect theory.
"""

import math
from pydantic import BaseModel


class AgentOutcome(BaseModel):
    """Outcome data for an agent used to compute sentiment change."""
    agent_id: str
    agent_type: str
    revenue_change_pct: float
    market_share_change_pct: float
    action_succeeded: bool  # Primary action achieved intended effect
    action_conflicted: bool  # Another agent directly countered this action
    loss_aversion_multiplier: float  # From agent profile (typically 2.0-2.5)
    herd_tendency: float  # 0.0-1.0, from profile
    prev_sentiment: float  # Previous fear-greed index (0-10)


class PeerBehaviorSummary(BaseModel):
    """Aggregate summary of peer behavior for herding effects."""
    aggressive_pct: float  # Fraction of peers taking aggressive actions (0.0-1.0)
    defensive_pct: float  # Fraction taking defensive/wait actions
    total_peers: int


class SentimentResult(BaseModel):
    """Result of sentiment computation for an agent."""
    agent_id: str
    new_sentiment: float  # Updated fear-greed index (0-10)
    delta: float  # Change from previous sentiment
    raw_utility: float  # Before normalization (for debugging)
    herd_adjustment: float  # Contribution from peer behavior


class SentimentEngine:
    """Computes fear-greed sentiment using prospect theory and herding.
    
    Uses Kahneman-Tversky prospect theory:
    - Gains are valued linearly
    - Losses are amplified by loss_aversion_multiplier
    - Normalized via tanh to prevent extreme values
    - Includes herding effect based on peer behavior
    - Regression to mean (5.0) prevents permanent extremes
    """

    # Weights for different outcome components
    REVENUE_WEIGHT = 0.50
    MARKET_SHARE_WEIGHT = 0.25
    ACTION_WEIGHT = 0.25
    
    # Action outcome utilities
    ACTION_SUCCESS_UTILITY = 5.0
    ACTION_CONFLICT_PENALTY_MULTIPLIER = 1.0  # Multiplied by loss_aversion

    # Normalization scale
    UTILITY_SCALE = 5.0

    # Regression to mean
    MOMENTUM = 0.85  # Weight on previous sentiment
    MEAN_PULL = 0.15  # Weight pulling toward 5.0

    # Herding
    HERD_STRENGTH = 1.0  # Maximum herd adjustment magnitude

    def _kt_utility(self, change_pct: float, loss_aversion: float) -> float:
        """Kahneman-Tversky utility function.
        
        Args:
            change_pct: Percentage change (positive = gain, negative = loss)
            loss_aversion: Multiplier for losses (typically 2.0-2.5)
            
        Returns:
            Utility value (gains linear, losses amplified)
        """
        if change_pct >= 0:
            # Gains: linear utility
            return change_pct
        else:
            # Losses: amplified by loss aversion
            return -loss_aversion * abs(change_pct)

    def compute_sentiment(
        self,
        outcome: AgentOutcome,
        peer_summary: PeerBehaviorSummary,
    ) -> SentimentResult:
        """Compute new sentiment for an agent based on outcomes and peers.
        
        Args:
            outcome: Agent's outcomes this round
            peer_summary: Aggregate peer behavior
            
        Returns:
            SentimentResult with new fear-greed index
        """
        lam = outcome.loss_aversion_multiplier

        # Step 1: Prospect theory utility
        revenue_utility = self._kt_utility(outcome.revenue_change_pct, lam)
        share_utility = self._kt_utility(outcome.market_share_change_pct, lam)
        
        # Action outcome utility
        if outcome.action_succeeded and not outcome.action_conflicted:
            action_utility = self.ACTION_SUCCESS_UTILITY
        elif outcome.action_conflicted:
            action_utility = -self.ACTION_CONFLICT_PENALTY_MULTIPLIER * lam * self.ACTION_SUCCESS_UTILITY
        else:
            action_utility = 0.0

        # Weighted combination
        raw_utility = (
            self.REVENUE_WEIGHT * revenue_utility +
            self.MARKET_SHARE_WEIGHT * share_utility +
            self.ACTION_WEIGHT * action_utility
        )

        # Step 2: Normalize via tanh
        normalized_delta = self.UTILITY_SCALE * math.tanh(raw_utility / self.UTILITY_SCALE)

        # Step 3: Herd adjustment
        # peer_greed_signal ranges from -1 (all defensive) to +1 (all aggressive)
        peer_greed_signal = (peer_summary.aggressive_pct - 0.5) * 2.0
        herd_delta = outcome.herd_tendency * self.HERD_STRENGTH * peer_greed_signal

        # Step 4: Momentum + regression to mean (5.0)
        new_sentiment = (
            self.MOMENTUM * outcome.prev_sentiment +
            self.MEAN_PULL * 5.0 +
            normalized_delta +
            herd_delta
        )

        # Clamp to [0.0, 10.0]
        new_sentiment = max(0.0, min(10.0, new_sentiment))

        return SentimentResult(
            agent_id=outcome.agent_id,
            new_sentiment=new_sentiment,
            delta=new_sentiment - outcome.prev_sentiment,
            raw_utility=raw_utility,
            herd_adjustment=herd_delta,
        )

    def compute_all(
        self,
        outcomes: list[AgentOutcome],
        peer_summary: PeerBehaviorSummary,
    ) -> dict[str, float]:
        """Compute sentiment for all agents.
        
        Args:
            outcomes: List of outcomes for all agents
            peer_summary: Aggregate peer behavior
            
        Returns:
            Dict mapping agent_id -> new_fear_greed_index
        """
        results = {}
        for outcome in outcomes:
            result = self.compute_sentiment(outcome, peer_summary)
            results[outcome.agent_id] = result.new_sentiment
        return results

    def build_peer_summary(
        self,
        actions: list[str],
        aggressive_action_ids: set[str],
    ) -> PeerBehaviorSummary:
        """Build peer behavior summary from round actions.
        
        Args:
            actions: List of primary action IDs from all agents
            aggressive_action_ids: Set of action IDs considered aggressive
            
        Returns:
            PeerBehaviorSummary with aggregate statistics
        """
        if not actions:
            return PeerBehaviorSummary(
                aggressive_pct=0.5,  # Neutral
                defensive_pct=0.5,
                total_peers=0,
            )

        aggressive_count = sum(1 for action in actions if action in aggressive_action_ids)
        total = len(actions)
        
        aggressive_pct = aggressive_count / total
        defensive_pct = 1.0 - aggressive_pct

        return PeerBehaviorSummary(
            aggressive_pct=aggressive_pct,
            defensive_pct=defensive_pct,
            total_peers=total,
        )

    def get_market_fear_greed(self, agent_sentiments: dict[str, float]) -> float:
        """Calculate market-wide fear-greed index.
        
        Simple average across all agents (could be weighted by info completeness).
        
        Args:
            agent_sentiments: Dict mapping agent_id -> fear_greed_index
            
        Returns:
            Market-wide average sentiment (0-10)
        """
        if not agent_sentiments:
            return 5.0  # Neutral

        return sum(agent_sentiments.values()) / len(agent_sentiments)

    def get_market_fear_greed_weighted(
        self,
        agent_sentiments: dict[str, float],
        agent_weights: dict[str, float],
    ) -> float:
        """Calculate weighted market fear-greed index.
        
        Args:
            agent_sentiments: agent_id -> sentiment
            agent_weights: agent_id -> weight (e.g., information_completeness)
            
        Returns:
            Weighted average sentiment
        """
        if not agent_sentiments:
            return 5.0

        total_weight = sum(agent_weights.get(aid, 1.0) for aid in agent_sentiments)
        if total_weight == 0:
            return 5.0

        weighted_sum = sum(
            sentiment * agent_weights.get(aid, 1.0)
            for aid, sentiment in agent_sentiments.items()
        )

        return weighted_sum / total_weight


# Aggressive actions by agent type (for peer summary construction)
AGGRESSIVE_ACTIONS = {
    "company": {
        "export_diversion", "joint_venture", "fdi", "domestic_expansion",
        "price_war", "lobby_government"
    },
    "government": {
        "retaliatory_tariff", "subsidy", "wto_dispute", "trade_negotiation",
        "capital_controls", "stimulus"
    },
    "regulator": {
        "open_investigation", "impose_provisional_duty", "recommend_definitive_duty",
        "fine_issued", "rule_proposed"
    },
    "consumer": {
        "switch_suppliers", "stockpile", "demand_subsidy"
    },
    "supplier": {
        "raise_prices", "capacity_investment"
    },
    "investor": {
        "increase_long", "open_short", "sector_rotation"
    },
}

# Defensive/wait actions
DEFENSIVE_ACTIONS = {
    "company": {"wait_and_observe", "hedge"},
    "government": {"do_nothing"},
    "regulator": {"no_action", "issue_cautionary_note"},
    "consumer": {"absorb_cost", "reduce_consumption"},
    "supplier": {"hold_prices", "hold_supply"},
    "investor": {"hold", "wait"},
}
