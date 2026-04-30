"""ResponseParser — Validates raw LLM JSON output and converts to RoundResponse.

This module implements Story 9 of the implementation plan:
- Six Pydantic validation models (one per agent type)
- JSON extraction from markdown code fences
- Action validation and coercion using difflib
- Semantic constraint checking
- Parse error handling with retry prompts
"""

import json
import re
import difflib
from typing import Any
from pydantic import BaseModel, field_validator, ValidationError

from models.agent_types import (
    AgentType,
    CompanyAction, GovernmentAction, RegulatorAction,
    ConsumerAction, SupplierAction, InvestorAction,
    PublicSignal, PrivateIntent, RoundResponse
)


# ============================================================================
# Exception Classes
# ============================================================================

class ParseError(Exception):
    """Raised when LLM output cannot be parsed successfully.
    
    Carries a retry_prompt that the BaseAgent injects into the conversation.
    """
    def __init__(self, message: str, retry_prompt: str, attempt: int):
        super().__init__(message)
        self.retry_prompt = retry_prompt
        self.attempt = attempt


# ============================================================================
# Base Agent Response Schema
# ============================================================================

class BaseAgentResponse(BaseModel):
    """Shared base fields for all agent response types."""
    action_id: str
    secondary_action_id: str | None = None
    reasoning: str
    public_signal: str
    private_signal: str
    confidence: float
    metrics_change: dict[str, float] = {}
    
    @field_validator('reasoning')
    @classmethod
    def validate_reasoning(cls, v: str) -> str:
        if len(v) < 20:
            raise ValueError("reasoning must be at least 20 characters")
        if len(v) > 800:
            v = v[:797] + "..."
        return v
    
    @field_validator('public_signal', 'private_signal')
    @classmethod
    def validate_signals(cls, v: str) -> str:
        if len(v) < 10:
            raise ValueError("signal must be at least 10 characters")
        if len(v) > 300:
            v = v[:297] + "..."
        return v
    
    @field_validator('confidence')
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        # Clamp to [0, 1] range
        return max(0.0, min(1.0, v))


# ============================================================================
# Six Agent-Specific Response Models
# ============================================================================

class CompanyResponse(BaseAgentResponse):
    """Response schema for company agents."""
    target_markets: list[str]  # ISO-2 country codes
    capex_commitment_usd_mn: float = 0.0
    lobby_target: str | None = None  # regulator agent_id if lobbying
    lobby_amount_usd_mn: float = 0.0
    production_change_pct: float = 0.0  # -100 to 200
    export_volume_mt: float | None = None


class GovernmentResponse(BaseAgentResponse):
    """Response schema for government agents."""
    policy_instrument: str  # Will validate as Literal in semantic check
    tariff_rate_pct: float | None = None  # 0–300
    subsidy_amount_usd_mn: float | None = None
    target_country_iso: str | None = None
    wto_notification_status: str = "not_required"
    political_feasibility: float  # 0.0–1.0
    retaliation_risk: float  # 0.0–1.0
    
    @field_validator('political_feasibility', 'retaliation_risk')
    @classmethod
    def validate_scores(cls, v: float) -> float:
        return max(0.0, min(1.0, v))


class RegulatorResponse(BaseAgentResponse):
    """Response schema for regulator agents."""
    enforcement_action: str  # Will validate as Literal in semantic check
    fine_amount_usd_mn: float | None = None
    target_entity_id: str | None = None
    rule_scope: str | None = None
    independence_score: float  # 0.0–1.0 — watch for capture
    
    @field_validator('independence_score')
    @classmethod
    def validate_independence(cls, v: float) -> float:
        return max(0.0, min(1.0, v))


class ConsumerResponse(BaseAgentResponse):
    """Response schema for consumer agents."""
    purchase_decision: str  # Will validate as Literal in semantic check
    volume_demand_mt: float
    max_price_usd_per_mt: float
    price_sensitivity: float  # 0.0–1.0
    
    @field_validator('price_sensitivity')
    @classmethod
    def validate_price_sensitivity(cls, v: float) -> float:
        return max(0.0, min(1.0, v))


class SupplierResponse(BaseAgentResponse):
    """Response schema for supplier agents."""
    supply_offer: str  # Will validate as Literal in semantic check
    volume_offered_mt: float
    min_price_usd_per_mt: float
    contract_length_months: int = 0  # 0 = spot
    destination_markets: list[str]


class InvestorResponse(BaseAgentResponse):
    """Response schema for investor agents."""
    investment_action: str  # Will validate as Literal in semantic check
    position_changes: dict[str, float]  # agent_id → USD mn delta
    portfolio_allocation_pct: dict[str, float]  # agent_id → new %, must sum to 100 ± 0.5
    leverage_ratio: float = 1.0  # 0–10
    macro_thesis: str
    
    @field_validator('macro_thesis')
    @classmethod
    def validate_macro_thesis(cls, v: str) -> str:
        if len(v) < 20:
            raise ValueError("macro_thesis must be at least 20 characters")
        return v
    
    @field_validator('leverage_ratio')
    @classmethod
    def validate_leverage(cls, v: float) -> float:
        return max(0.0, min(10.0, v))


# ============================================================================
# Registry: Map agent types to response models
# ============================================================================

RESPONSE_MODELS: dict[str, type[BaseAgentResponse]] = {
    AgentType.company.value: CompanyResponse,
    AgentType.government.value: GovernmentResponse,
    AgentType.regulator.value: RegulatorResponse,
    AgentType.consumer.value: ConsumerResponse,
    AgentType.supplier.value: SupplierResponse,
    AgentType.investor.value: InvestorResponse,
}


# ============================================================================
# Valid Actions Registry
# ============================================================================

_VALID_ACTIONS: dict[str, set[str]] = {
    AgentType.company.value: {action.value for action in CompanyAction},
    AgentType.government.value: {action.value for action in GovernmentAction},
    AgentType.regulator.value: {action.value for action in RegulatorAction},
    AgentType.consumer.value: {action.value for action in ConsumerAction},
    AgentType.supplier.value: {action.value for action in SupplierAction},
    AgentType.investor.value: {action.value for action in InvestorAction},
}


# ============================================================================
# ResponseParser Class
# ============================================================================

class ResponseParser:
    """Validates raw LLM JSON output and converts to RoundResponse.
    
    Handles:
    - JSON extraction from markdown code fences
    - Pydantic validation against role-specific schemas
    - Action ID validation and fuzzy matching
    - Semantic constraint checking (cash limits, portfolio sums, etc.)
    - Parse error accumulation for diagnostics
    """
    
    def __init__(self):
        self.parse_errors: list[str] = []
    
    def parse(
        self,
        raw: str,
        agent_type: str,
        agent_state: dict,
        available_action_ids: list[str],
        attempt: int = 0
    ) -> BaseAgentResponse:
        """Parse raw LLM output into a validated agent response.
        
        Args:
            raw: Raw LLM output (may include markdown fences)
            agent_type: One of the AgentType enum values
            agent_state: Current agent state dict for semantic validation
            available_action_ids: List of valid action IDs for this agent
            attempt: Retry attempt number (0-indexed)
        
        Returns:
            Validated BaseAgentResponse subclass instance
        
        Raises:
            ParseError: If parsing fails with retry prompt
        """
        errors = []
        
        # Step 1: Extract JSON from markdown fences
        try:
            json_str = self._strip_fences(raw)
        except Exception as e:
            error_msg = f"Failed to extract JSON: {e}"
            errors.append(error_msg)
            self.parse_errors.append(error_msg)
            raise ParseError(
                error_msg,
                self._build_retry_prompt(errors, raw, attempt),
                attempt
            )
        
        # Step 2: Parse JSON
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON syntax: {e}"
            errors.append(error_msg)
            self.parse_errors.append(error_msg)
            raise ParseError(
                error_msg,
                self._build_retry_prompt(errors, raw, attempt),
                attempt
            )
        
        # Step 3: Validate action_id and coerce if needed
        action_id = data.get("action_id", "")
        if action_id not in available_action_ids:
            # Try fuzzy matching
            valid_actions = _VALID_ACTIONS.get(agent_type, set())
            matches = difflib.get_close_matches(action_id, valid_actions, n=1, cutoff=0.6)
            if matches:
                print(f"[WARN] Coerced action '{action_id}' → '{matches[0]}'")
                data["action_id"] = matches[0]
            else:
                error_msg = f"Invalid action_id '{action_id}'. Must be one of: {', '.join(available_action_ids)}"
                errors.append(error_msg)
                self.parse_errors.append(error_msg)
                raise ParseError(
                    error_msg,
                    self._build_retry_prompt(errors, raw, attempt),
                    attempt
                )
        
        # Step 4: Pydantic validation
        model_class = RESPONSE_MODELS.get(agent_type)
        if not model_class:
            raise ValueError(f"Unknown agent_type: {agent_type}")
        
        try:
            validated = model_class.model_validate(data)
        except ValidationError as e:
            error_msg = f"Pydantic validation failed: {e}"
            errors.append(error_msg)
            self.parse_errors.append(error_msg)
            raise ParseError(
                error_msg,
                self._build_retry_prompt(errors, raw, attempt),
                attempt
            )
        
        # Step 5: Semantic constraint checks
        try:
            self._check_semantic_constraints(validated, agent_type, agent_state)
        except ValueError as e:
            error_msg = str(e)
            errors.append(error_msg)
            self.parse_errors.append(error_msg)
            raise ParseError(
                error_msg,
                self._build_retry_prompt(errors, raw, attempt),
                attempt
            )
        
        return validated
    
    def _strip_fences(self, raw: str) -> str:
        """Extract JSON from markdown code fences or raw text."""
        # Try to find JSON within code fences
        fence_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
        match = re.search(fence_pattern, raw, re.DOTALL)
        if match:
            return match.group(1)
        
        # Fallback: extract any JSON object from the text
        json_pattern = r'\{.*\}'
        match = re.search(json_pattern, raw, re.DOTALL)
        if match:
            return match.group(0)
        
        raise ValueError("No JSON object found in response")
    
    def _check_semantic_constraints(
        self,
        response: BaseAgentResponse,
        agent_type: str,
        agent_state: dict
    ) -> None:
        """Check role-specific semantic constraints.
        
        Raises ValueError if constraints are violated.
        """
        # Company: cash limits
        if agent_type == AgentType.company.value and isinstance(response, CompanyResponse):
            cash_usd_mn = agent_state.get("cash_usd_mn", float('inf'))
            total_commitment = response.capex_commitment_usd_mn + response.lobby_amount_usd_mn
            if total_commitment > 0.8 * cash_usd_mn:
                raise ValueError(
                    f"Total commitment (${total_commitment:.1f}M) exceeds 80% of available cash (${cash_usd_mn:.1f}M)"
                )
        
        # Investor: portfolio allocation must sum to ~100%
        if agent_type == AgentType.investor.value and isinstance(response, InvestorResponse):
            total_allocation = sum(response.portfolio_allocation_pct.values())
            if not (99.5 <= total_allocation <= 100.5):
                raise ValueError(
                    f"Portfolio allocation must sum to 100% (got {total_allocation:.1f}%)"
                )
    
    def _build_retry_prompt(self, errors: list[str], original_raw: str, attempt: int) -> str:
        """Build a retry prompt for the LLM."""
        error_list = "\n".join(f"{i+1}. {err}" for i, err in enumerate(errors))
        truncated_raw = original_raw[:500] + "..." if len(original_raw) > 500 else original_raw
        
        return f"""Your previous response contained errors. Attempt {attempt + 2} of 3.

Errors:
{error_list}

Your previous response:
---
{truncated_raw}
---

Resubmit corrected JSON only. No markdown, no explanation."""
    
    def to_round_response(
        self,
        parsed: BaseAgentResponse,
        agent_id: str,
        round_num: int,
        raw_output: str
    ) -> RoundResponse:
        """Convert a validated BaseAgentResponse to RoundResponse."""
        # Build PublicSignal from public_signal field
        signals = []
        if parsed.public_signal:
            signals.append(PublicSignal(
                from_agent=agent_id,
                to_agent=None,  # Broadcast
                content=parsed.public_signal,
                signal_type="market_signal",
                round=round_num
            ))
        
        # Build PrivateIntent from private_signal field
        private_intent = None
        if parsed.private_signal:
            private_intent = PrivateIntent(
                content=parsed.private_signal,
                target_agent=None
            )
        
        return RoundResponse(
            agent_id=agent_id,
            round=round_num,
            primary_action=parsed.action_id,
            secondary_action=parsed.secondary_action_id,
            assessment=parsed.reasoning,
            confidence=parsed.confidence,
            impact_areas=[],  # Will be filled by simulation engine
            metrics_change=parsed.metrics_change,
            signals_to_ecosystem=signals,
            private_intent=private_intent,
            raw_llm_output=raw_output,
            is_fallback=False
        )
