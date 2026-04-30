"""PromptBuilder — System prompts and round messages for all 6 agent types.

This module implements Story 11 of the implementation plan:
- Builds role-specific system prompts with persona, objectives, constraints
- Assembles round messages with shock context, market conditions, and available actions
- Filters available actions based on agent state and constraints
- Provides inline JSON examples for each agent type
"""

from typing import Any
from models.agent_types import AgentProfile, AgentState, AgentType, RoundResponse
from models.world_state import RoundContext


# ============================================================================
# Action Descriptions and Costs
# ============================================================================

ACTION_DESCRIPTIONS = {
    # Company actions
    "export_diversion": "Reroute export volumes from US to EU/ASEAN. Requires 2–3 rounds to fully execute. Cost: 5–15% cash.",
    "joint_venture": "Form partnership with local firm in target market. Cost: 10–20% cash.",
    "fdi": "Establish wholly-owned foreign subsidiary. Requires significant capital. Cost: 30–50% cash.",
    "licensing": "License technology/brand to foreign partners. Low cost, lower control. Cost: 1–5% cash.",
    "domestic_expansion": "Expand domestic capacity to absorb diverted exports. Cost: 15–30% cash.",
    "price_war": "Aggressively cut prices to defend market share. Risky, margin-destroying. Cost: Variable.",
    "lobby_government": "Lobby home government/regulator for favorable policy. Cost: 2–10% cash.",
    "hedge": "Financial hedging via derivatives to reduce currency/commodity risk. Cost: 1–3% cash.",
    "wait_and_observe": "Take no action this round. Preserve optionality. Cost: $0.",
    
    # Government actions
    "retaliatory_tariff": "Impose counter-tariffs on US exports. Triggers trade war escalation risk.",
    "subsidy": "Direct fiscal support to domestic steel industry. Budget impact: 0.5–2% deficit.",
    "wto_dispute": "File formal WTO complaint. Takes 12–24 months to resolve.",
    "trade_negotiation": "Bilateral talks to de-escalate. Requires diplomatic capital.",
    "capital_controls": "Restrict capital outflows to stabilize currency. Market distortion risk.",
    "stimulus": "Broad fiscal or monetary stimulus to offset demand shock. Deficit impact: 1–3%.",
    "do_nothing": "Maintain current policy stance. Let market adjust naturally.",
    
    # Regulator actions
    "open_investigation": "Initiate anti-dumping or safeguard investigation. 6–12 month duration.",
    "impose_provisional_duty": "Impose temporary duties pending investigation conclusion. Max 30%.",
    "recommend_definitive_duty": "Recommend final duties to government. Max duration: 5 years.",
    "reject_petition": "Reject industry petition for lack of evidence. Politically costly.",
    "issue_cautionary_note": "Public statement without enforcement. Signaling only.",
    
    # Consumer actions
    "switch_suppliers": "Change sourcing from imports to domestic or alternative countries.",
    "stockpile": "Build inventory ahead of expected price increases. Working capital impact.",
    "absorb_cost": "Accept higher input costs without passing through to customers. Margin compression.",
    "pass_through_pricing": "Raise output prices to offset input cost inflation. Demand risk.",
    "demand_subsidy": "Petition government for input cost relief. Political uncertainty.",
    
    # Supplier actions
    "raise_prices": "Increase prices in response to demand strength or cost pressures.",
    "hold_prices": "Maintain current pricing despite market conditions.",
    "lower_prices": "Cut prices to defend volume in competitive environment.",
    "diversify_customers": "Expand customer base to reduce concentration risk.",
    "capacity_investment": "Expand production capacity. Long-term commitment. Cost: 20–40% reserves.",
    "negotiate_long_term": "Offer long-term contracts for price/volume stability.",
    
    # Investor actions
    "buy": "Increase long positions in steel sector equities. Bullish bet.",
    "sell": "Reduce long positions or exit entirely. Bearish signal.",
    "short": "Open short positions betting on price declines. High risk.",
    "fx_bet": "Currency speculation on INR/USD moves. Leverage available.",
    "sector_rotation": "Rotate out of steel into alternative sectors (tech, pharma, etc.).",
    "wait": "Hold current positions. No portfolio changes this round.",
}


# ============================================================================
# PromptBuilder Class
# ============================================================================

class PromptBuilder:
    """Builds system prompts and round messages for all agent types."""
    
    def build_system_prompt(
        self,
        profile: AgentProfile,
        capture_bias: str | None = None
    ) -> str:
        """Build the system prompt defining an agent's persona and constraints.
        
        Args:
            profile: Agent profile with objectives, constraints, behavioral data
            capture_bias: Optional capture bias text injected by CaptureEngine
        
        Returns:
            Complete system prompt string
        """
        sections = []
        
        # Section A: Persona
        sections.append(f"""You are {profile.name}, a {profile.agent_type.value} in the global steel/EV economy.

Your objectives:
{self._format_list(profile.objectives)}

Your constraints (you MUST respect these):
{self._format_list(profile.constraints)}

Behavioral profile:
- Loss aversion: {profile.data.get('loss_aversion_multiplier', 2.0)}× (you weight losses this much heavier than equivalent gains)
- Risk appetite: {profile.data.get('risk_appetite', 'moderate')}
- Herd tendency: {profile.data.get('herd_tendency', 0.5)} (0=contrarian, 1=follows consensus)
""")
        
        # Add role-specific context
        if profile.agent_type == AgentType.company:
            sections.append(f"""
Your fear-greed index is currently {profile.data.get('fear_greed_index', 5.0)}/10.
Below 4 = risk-averse. Above 7 = confident and may pursue aggressive actions.
Financial health: {profile.data.get('financial_health', 0.7)}/1.0
""")
        
        # Section B: Capture bias (conditional)
        if capture_bias:
            sections.append(f"\n{capture_bias}\n")
        
        # Check for high capture in government
        if profile.agent_type == AgentType.government:
            capture_score = profile.data.get('capture_score', 0.0)
            if capture_score > 0.3:
                sections.append(f"""
Note: You have received significant lobbying pressure from domestic industry. 
This may influence your policy calculus as you balance stakeholder interests.
""")
        
        return "\n".join(sections)
    
    def build_round_message(
        self,
        context: RoundContext,
        profile: AgentProfile,
        memory: list[RoundResponse]
    ) -> str:
        """Build the round-specific user message with context and decision prompt.
        
        Args:
            context: Current round context (signals, market state, etc.)
            profile: Agent profile
            memory: Agent's memory of previous decisions (last 2 rounds used)
        
        Returns:
            Complete round message string
        """
        sections = []
        
        # Section 1: Round + Shock
        sections.append(f"""=== ROUND {context.round} OF 5 — ECONOMIC SHOCK UPDATE ===

{context.shock.get('context', 'No shock context available.')}
""")
        
        # Section 2: Your Position
        sections.append(f"""
YOUR CURRENT POSITION:

Financial health: {context.own_state.financial_health:.2f}/1.0
Fear-greed index: {context.own_state.fear_greed_index:.1f}/10
Active actions: {', '.join(context.own_state.active_actions) if context.own_state.active_actions else 'None'}

Key metrics:
{self._format_metrics(context.own_state.metrics)}
""")
        
        # Section 3: Market Conditions
        sections.append(f"""
MARKET CONDITIONS:

{self._format_market_state(context.market_state)}
""")
        
        # Section 4: Market Intelligence
        if context.visible_signals:
            signals_text = "\n".join(
                f"- [{signal.from_agent}]: {signal.content}" 
                for signal in context.visible_signals[-5:]  # Last 5 signals only
            )
            sections.append(f"""
MARKET INTELLIGENCE (recent signals from other agents):

{signals_text}
""")
        else:
            sections.append("""
MARKET INTELLIGENCE:

No prior signals available. You are deciding under full uncertainty.
""")
        
        # Section 5: Competitive Effects
        if context.competitive_effects:
            effects_text = "\n".join(
                f"- {effect}: {magnitude:.2f}" 
                for effect, magnitude in context.competitive_effects.items()
            )
            sections.append(f"""
COMPETITIVE EFFECTS:

{effects_text}
""")
        
        # Section 6: Available Actions
        available_actions = self.get_available_actions(profile, context.own_state)
        actions_text = self._format_available_actions(available_actions)
        sections.append(f"""
AVAILABLE ACTIONS THIS ROUND:

{actions_text}
""")
        
        # Section 7: Previous Decisions (last 2 rounds)
        if memory:
            prev_decisions = "\n".join(
                f"Round {resp.round}: {resp.primary_action} — {resp.assessment[:100]}..." 
                for resp in memory[-2:]
            )
            sections.append(f"""
YOUR PREVIOUS DECISIONS:

{prev_decisions}
""")
        
        # Section 8: Response Format
        sections.append(f"""
RESPONSE FORMAT:

Respond with valid JSON only. No markdown, no explanation outside the JSON.

{self._get_response_schema_example(profile.agent_type)}
""")
        
        return "\n".join(sections)
    
    def get_available_actions(
        self,
        profile: AgentProfile,
        state: AgentState
    ) -> list[dict[str, Any]]:
        """Get available actions with availability status and constraints.
        
        Args:
            profile: Agent profile
            state: Current agent state
        
        Returns:
            List of dicts: {"action_id": str, "available": bool, "reason": str | None}
        """
        actions = []
        
        # Get role-specific actions
        if profile.agent_type == AgentType.company:
            from models.agent_types import CompanyAction
            for action in CompanyAction:
                available, reason = self._check_company_action_availability(
                    action.value, profile, state
                )
                actions.append({
                    "action_id": action.value,
                    "available": available,
                    "reason": reason
                })
        
        elif profile.agent_type == AgentType.government:
            from models.agent_types import GovernmentAction
            for action in GovernmentAction:
                actions.append({"action_id": action.value, "available": True, "reason": None})
        
        elif profile.agent_type == AgentType.regulator:
            from models.agent_types import RegulatorAction
            for action in RegulatorAction:
                actions.append({"action_id": action.value, "available": True, "reason": None})
        
        elif profile.agent_type == AgentType.consumer:
            from models.agent_types import ConsumerAction
            for action in ConsumerAction:
                actions.append({"action_id": action.value, "available": True, "reason": None})
        
        elif profile.agent_type == AgentType.supplier:
            from models.agent_types import SupplierAction
            for action in SupplierAction:
                actions.append({"action_id": action.value, "available": True, "reason": None})
        
        elif profile.agent_type == AgentType.investor:
            from models.agent_types import InvestorAction
            for action in InvestorAction:
                actions.append({"action_id": action.value, "available": True, "reason": None})
        
        return actions
    
    def _check_company_action_availability(
        self,
        action: str,
        profile: AgentProfile,
        state: AgentState
    ) -> tuple[bool, str | None]:
        """Check if a company action is available given current constraints."""
        cash_usd_mn = profile.data.get("cash_reserves_usd_bn", 0) * 1000
        
        # FDI requires significant capital
        if action == "fdi":
            if cash_usd_mn < 2000:
                return False, f"Insufficient cash reserves (${cash_usd_mn:.0f}M < $2000M required)"
        
        # Joint venture requires moderate capital
        if action == "joint_venture":
            if cash_usd_mn < 500:
                return False, f"Insufficient cash reserves (${cash_usd_mn:.0f}M < $500M required)"
        
        # Domestic expansion requires significant capex
        if action == "domestic_expansion":
            if cash_usd_mn < 1000:
                return False, f"Insufficient cash reserves (${cash_usd_mn:.0f}M < $1000M required)"
        
        return True, None
    
    def _format_list(self, items: list[str]) -> str:
        """Format a list as numbered items."""
        return "\n".join(f"{i+1}. {item}" for i, item in enumerate(items))
    
    def _format_metrics(self, metrics: dict[str, float]) -> str:
        """Format metrics dict as bullet list."""
        if not metrics:
            return "No metrics available."
        return "\n".join(f"- {k}: {v:.2f}" for k, v in metrics.items())
    
    def _format_market_state(self, market_state: dict[str, Any]) -> str:
        """Format market state as bullet list."""
        lines = []
        for commodity, state in market_state.items():
            price = state.spot_price if hasattr(state, 'spot_price') else state.get('spot_price', 0)
            change = state.price_change_pct if hasattr(state, 'price_change_pct') else state.get('price_change_pct')
            change_str = f" ({change:+.1f}%)" if change is not None else ""
            lines.append(f"- {commodity}: ${price:.2f}/MT{change_str}")
        return "\n".join(lines) if lines else "No market data available."
    
    def _format_available_actions(self, actions: list[dict]) -> str:
        """Format available actions with descriptions and availability."""
        lines = []
        for action in actions:
            action_id = action["action_id"]
            desc = ACTION_DESCRIPTIONS.get(action_id, "No description available.")
            
            if action["available"]:
                lines.append(f"`{action_id}` — {desc}")
            else:
                reason = action.get("reason", "Not available")
                lines.append(f"[LOCKED] `{action_id}` — {reason}")
        
        return "\n".join(lines)
    
    def _get_response_schema_example(self, agent_type: AgentType) -> str:
        """Get role-specific JSON schema example."""
        if agent_type == AgentType.company:
            return """{
  "action_id": "export_diversion",
  "secondary_action_id": null,
  "reasoning": "US tariffs make direct exports unviable. Redirecting 1.5M MT to EU/ASEAN markets where we have existing relationships. This preserves revenue at cost of 8-12% margin compression due to increased logistics and competitive pricing pressure in those markets.",
  "public_signal": "Tata Steel announces strategic pivot to European and Asian markets following US trade restrictions.",
  "private_signal": "Board has authorized up to $800M for trade finance and working capital to support the diversion. Expect 2-3 quarters before new routes are fully operational.",
  "confidence": 0.75,
  "target_markets": ["EU", "ASEAN"],
  "capex_commitment_usd_mn": 450,
  "lobby_target": null,
  "lobby_amount_usd_mn": 0,
  "production_change_pct": 5,
  "export_volume_mt": 1500000,
  "metrics_change": {"revenue_change_pct": -12, "margin_change_pct": -8}
}"""
        
        elif agent_type == AgentType.government:
            return """{
  "action_id": "retaliatory_tariff",
  "secondary_action_id": "subsidy",
  "reasoning": "US Section 232 tariffs are economically and politically unacceptable. Imposing 25% counter-tariffs on US agricultural exports ($3B annually) as proportionate response. Simultaneously offering $500M subsidy package to domestic steel producers to cushion export loss.",
  "public_signal": "Government of India announces retaliatory tariffs on US goods and relief package for steel industry.",
  "private_signal": "Cabinet consensus is fragile - Finance Minister concerned about fiscal impact, but PMO prioritized political signaling. WTO dispute to be filed within 30 days as backup strategy.",
  "confidence": 0.65,
  "policy_instrument": "tariff",
  "tariff_rate_pct": 25,
  "subsidy_amount_usd_mn": 500,
  "target_country_iso": "US",
  "wto_notification_status": "notified",
  "political_feasibility": 0.8,
  "retaliation_risk": 0.9,
  "metrics_change": {"fiscal_deficit_pct": 0.3}
}"""
        
        elif agent_type == AgentType.regulator:
            return """{
  "action_id": "open_investigation",
  "secondary_action_id": null,
  "reasoning": "Domestic steel industry petition meets prima facie evidence threshold for anti-dumping investigation against Chinese imports. Opening formal investigation under WTO-compliant procedures. Expected duration: 12 months.",
  "public_signal": "DGTR initiates anti-dumping investigation on Chinese steel imports following industry petition.",
  "private_signal": "Industry lobbying has been intense but evidence of material injury is independently verifiable. Proceeding on merits.",
  "confidence": 0.85,
  "enforcement_action": "investigation_open",
  "fine_amount_usd_mn": null,
  "target_entity_id": null,
  "rule_scope": "Chinese flat-rolled steel imports",
  "independence_score": 0.75,
  "metrics_change": {}
}"""
        
        elif agent_type == AgentType.consumer:
            return """{
  "action_id": "switch_suppliers",
  "secondary_action_id": "stockpile",
  "reasoning": "US steel prices up 40% post-tariff. Switching 60% of procurement to domestic suppliers and Korean imports. Building 3-month inventory buffer to hedge against further volatility.",
  "public_signal": "Industrial consumers accelerating shift to domestic steel sourcing amid tariff-driven price surge.",
  "private_signal": "Supplier qualification for Korean mills will take 2 months minimum. Margin pressure is acute in the interim.",
  "confidence": 0.70,
  "purchase_decision": "buy_domestic",
  "volume_demand_mt": 50000,
  "max_price_usd_per_mt": 720,
  "price_sensitivity": 0.75,
  "metrics_change": {"input_cost_change_pct": 22}
}"""
        
        elif agent_type == AgentType.supplier:
            return """{
  "action_id": "raise_prices",
  "secondary_action_id": "negotiate_long_term",
  "reasoning": "Steel demand surge from export diversion creating tight domestic market. Raising iron ore prices 12% to capture scarcity value. Offering 2-year fixed-price contracts at 8% premium to lock in relationships.",
  "public_signal": "Iron ore suppliers announce 12% price increase citing strong demand and supply constraints.",
  "private_signal": "Contract negotiations with Tata and JSW ongoing - they're price-sensitive but have limited alternatives short-term.",
  "confidence": 0.80,
  "supply_offer": "increase_supply",
  "volume_offered_mt": 55000000,
  "min_price_usd_per_mt": 128,
  "contract_length_months": 24,
  "destination_markets": ["IN"],
  "metrics_change": {"margin_pct": 15}
}"""
        
        elif agent_type == AgentType.investor:
            return """{
  "action_id": "sell",
  "secondary_action_id": null,
  "reasoning": "US tariffs create structural headwind for Indian steel exporters. Reducing steel sector allocation from 4.2% to 2.0% of AUM ($4B → $2B). Rotating into domestic-focused pharma and IT services which benefit from INR weakness.",
  "public_signal": "FII steel holdings decline $2B amid tariff uncertainty.",
  "private_signal": "Client redemption requests spiking in steel-heavy funds. Need liquidity buffer.",
  "confidence": 0.70,
  "investment_action": "sector_rotation",
  "position_changes": {"tata_steel": -1500, "jsw_steel": -500, "pharma_sector": 2000},
  "portfolio_allocation_pct": {"steel": 2.0, "pharma": 6.0, "it_services": 8.0, "other": 84.0},
  "leverage_ratio": 1.0,
  "macro_thesis": "Tariff shock is persistent not transitory. Steel margins will compress 300bps+ over next 4 quarters. Domestic demand sectors with pricing power are better risk-adjusted bets.",
  "metrics_change": {"steel_allocation_pct": -2.2}
}"""
        
        else:
            return "{}"
    
