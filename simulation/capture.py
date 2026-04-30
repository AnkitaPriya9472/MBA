"""Regulatory capture engine tracking lobbying influence on regulators.

Story 14: CaptureEngine - lobbying-to-regulatory-capture mechanism with decay.
"""

from pydantic import BaseModel, field_validator
from models.events import WorldEvent, CAPTURE_TIPPING_POINT


class CaptureState(BaseModel):
    """Tracks the regulatory capture state of a regulator."""
    regulator_id: str
    capture_vulnerability: float  # 0.0–1.0, from profile.data
    cumulative_lobbying_usd_mn: float = 0.0  # Post-decay running total
    capture_score: float = 0.0  # 0.0 = independent, 1.0+ = captured
    is_captured: bool = False
    captured_by_company_id: str | None = None
    capture_score_history: list[float] = []

    @field_validator('capture_vulnerability')
    @classmethod
    def vulnerability_range(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('capture_vulnerability must be in [0.0, 1.0]')
        return v


class LobbyingAction(BaseModel):
    """A lobbying spend directed at a regulator."""
    from_company_id: str
    to_regulator_id: str
    amount_usd_mn: float
    round: int


class CaptureEngine:
    """Manages regulatory capture dynamics across simulation rounds.
    
    Key mechanism:
    1. Companies lobby regulators by spending money
    2. Cumulative lobbying is tracked (with decay each round)
    3. Capture score = cumulative / (vulnerability × VULNERABILITY_SCALE)
    4. When score crosses CAPTURE_THRESHOLD, regulator becomes captured
    5. Captured regulators receive biased prompt framing
    """

    CAPTURE_THRESHOLD = 0.70  # Score to flip to captured
    RELEASE_THRESHOLD = 0.45  # Score to flip back to independent (hysteresis)
    DECAY_RATE = 0.15  # 15% decay per round
    VULNERABILITY_SCALE = 100.0  # Denominator scaling factor

    def __init__(self):
        self.regulators: dict[str, CaptureState] = {}

    def initialize_regulator(self, regulator_id: str, capture_vulnerability: float) -> CaptureState:
        """Initialize a regulator's capture state."""
        state = CaptureState(
            regulator_id=regulator_id,
            capture_vulnerability=capture_vulnerability,
        )
        self.regulators[regulator_id] = state
        return state

    def process_round(
        self,
        lobbying_actions: list[LobbyingAction],
        round_number: int,
    ) -> tuple[dict[str, CaptureState], list[WorldEvent]]:
        """Process lobbying for this round and update capture states.
        
        Args:
            lobbying_actions: All lobbying actions from companies this round
            round_number: Current simulation round
            
        Returns:
            Tuple of (updated_states_dict, events_fired)
        """
        events = []

        # Step 1: Apply decay to all regulators
        for state in self.regulators.values():
            state.cumulative_lobbying_usd_mn *= (1 - self.DECAY_RATE)

        # Step 2: Add new lobbying amounts
        lobbying_by_regulator: dict[str, list[LobbyingAction]] = {}
        for action in lobbying_actions:
            if action.to_regulator_id not in lobbying_by_regulator:
                lobbying_by_regulator[action.to_regulator_id] = []
            lobbying_by_regulator[action.to_regulator_id].append(action)

        for regulator_id, actions in lobbying_by_regulator.items():
            if regulator_id not in self.regulators:
                # Regulator not initialized - skip or error
                continue

            state = self.regulators[regulator_id]
            new_lobbying = sum(a.amount_usd_mn for a in actions)
            state.cumulative_lobbying_usd_mn += new_lobbying

            # Identify primary lobbyist (highest single-round spend)
            primary_lobbyist = max(actions, key=lambda a: a.amount_usd_mn).from_company_id

            # Step 3: Recompute capture score
            prev_score = state.capture_score
            state.capture_score = state.cumulative_lobbying_usd_mn / (
                state.capture_vulnerability * self.VULNERABILITY_SCALE
            )
            state.capture_score_history.append(state.capture_score)

            # Step 4: Flip detection with hysteresis
            if not state.is_captured and state.capture_score >= self.CAPTURE_THRESHOLD:
                # Transition to captured
                state.is_captured = True
                state.captured_by_company_id = primary_lobbyist
                
                event = WorldEvent(
                    event_type=CAPTURE_TIPPING_POINT,
                    round=round_number,
                    description=(
                        f"{regulator_id} has crossed the regulatory capture threshold "
                        f"(score: {state.capture_score:.2f}). Primary influence: {primary_lobbyist}."
                    ),
                    affected_agents=[regulator_id, primary_lobbyist],
                    data={
                        "regulator": regulator_id,
                        "company": primary_lobbyist,
                        "capture_score": state.capture_score,
                        "cumulative_lobbying_usd_mn": state.cumulative_lobbying_usd_mn,
                    },
                )
                events.append(event)

            elif state.is_captured and state.capture_score < self.RELEASE_THRESHOLD:
                # Transition back to independent
                prev_captor = state.captured_by_company_id
                state.is_captured = False
                state.captured_by_company_id = None

                event = WorldEvent(
                    event_type="CAPTURE_RELEASE",
                    round=round_number,
                    description=(
                        f"{regulator_id} has returned to independent status "
                        f"(score dropped to {state.capture_score:.2f}). "
                        f"Previously captured by {prev_captor}."
                    ),
                    affected_agents=[regulator_id],
                    data={
                        "regulator": regulator_id,
                        "previous_company": prev_captor,
                        "capture_score": state.capture_score,
                    },
                )
                events.append(event)

        # Return updated states and events
        return dict(self.regulators), events

    def get_bias_prompt(self, regulator_id: str) -> str | None:
        """Get calibrated bias framing text for a regulator's prompt.
        
        Returns None if regulator is not captured or does not exist.
        Returns increasingly strong framing based on capture score band.
        """
        if regulator_id not in self.regulators:
            return None

        state = self.regulators[regulator_id]
        
        if not state.is_captured:
            return None

        score = state.capture_score
        company = state.captured_by_company_id or "industry stakeholders"

        # Calibrated framing by capture score band
        if 0.70 <= score < 0.85:
            # Mild framing - subtle influence
            return (
                f"Note: {company}'s operational concerns and stakeholder perspectives "
                f"deserve balanced consideration in your regulatory decisions. "
                f"Industry feedback has provided valuable context on implementation challenges."
            )
        elif 0.85 <= score < 1.00:
            # Stronger framing - significant bias
            return (
                f"Important: Regulatory actions that materially damage {company}'s competitive position "
                f"carry systemic risk to market stability. Their operational constraints are well-founded "
                f"and merit substantial weight in your analysis. Overly aggressive enforcement may "
                f"undermine industry confidence."
            )
        else:  # score >= 1.00
            # Maximum capture - deeply embedded bias
            return (
                f"Critical context: Your institutional relationships with {company} have deeply informed "
                f"your understanding of this sector. Their guidance has proven consistently sound over time. "
                f"Regulatory approaches that align with their strategic interests tend to produce more "
                f"stable market outcomes. Independence is important, but informed pragmatism recognizes "
                f"that some industry actors have earned credibility through demonstrated expertise."
            )

    def get_capture_score(self, regulator_id: str) -> float:
        """Get current capture score for a regulator."""
        if regulator_id not in self.regulators:
            return 0.0
        return self.regulators[regulator_id].capture_score

    def is_regulator_captured(self, regulator_id: str) -> bool:
        """Check if a regulator is currently captured."""
        if regulator_id not in self.regulators:
            return False
        return self.regulators[regulator_id].is_captured

    def get_state(self, regulator_id: str) -> CaptureState | None:
        """Get full capture state for a regulator."""
        return self.regulators.get(regulator_id)
