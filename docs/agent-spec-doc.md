# Agent Architecture Specification

> **Purpose:** This document defines every agent type in the simulation with enough detail to convert directly to code. Each agent section specifies identity, state, decision logic, behavioral model, and structured output. The *interaction protocol* between agents is covered in a separate document.

---

## How to read this document

Each agent type follows the same structure:

1. **Role & theoretical grounding** — what this agent represents and which IB/economics frameworks justify its behavior
2. **Initialization profile** — the JSON schema for creating an instance, with real-world data sources
3. **State variables** — what this agent tracks across simulation rounds (its "memory")
4. **Decision menu** — the constrained set of actions available each round, with costs, timelines, and reversibility
5. **Behavioral parameters** — cognitive biases, cultural dimensions, and personality traits embedded in the LLM prompt
6. **Institutional context** — which rules, laws, and constraints shape this agent's behavior
7. **System prompt template** — the actual LLM prompt skeleton
8. **Output schema** — the structured JSON response expected from the LLM each round
9. **Example profile** — one fully worked instance with real data

---

## Agent Type 1: Company Agent

### 1.1 Role & theoretical grounding

The Company Agent represents a publicly listed manufacturing firm operating in international markets. It is the *primary strategic actor* in the simulation — the entity whose decisions we ultimately want to forecast.

**Theoretical anchors:**
- **Porter's Diamond** — the company's competitive advantage is shaped by factor conditions, demand conditions, related industries, and firm strategy/rivalry in its home country
- **Entry mode theory (Dunning's OLI Paradigm)** — the company chooses between exporting, licensing, JV, and FDI based on its ownership advantages (O), location advantages of the target (L), and internalization advantages (I)
- **Behavioral theory of the firm (Cyert & March)** — the company satisfices rather than optimizes, searches locally before globally, and is influenced by dominant coalitions within the firm
- **Transaction cost economics (Williamson)** — make-or-buy decisions and governance mode choices are driven by asset specificity, uncertainty, and frequency of transactions

### 1.2 Initialization profile schema

```json
{
  "agent_id": "string — unique identifier (e.g., 'tata_steel')",
  "name": "string — display name",
  "agent_type": "company",
  "sector": "string — industry sector (e.g., 'steel', 'automotive')",
  "home_country": "string — country code (e.g., 'IN', 'US')",

  "financials": {
    "revenue_usd_mn": "number — latest annual revenue",
    "export_revenue_pct": "number — 0-100, percentage of revenue from exports",
    "export_markets": {
      "<country_code>": {
        "revenue_pct": "number — share of total export revenue",
        "tariff_rate_current": "number — current tariff rate in that market (0-100)",
        "product_categories": ["string — what products go to this market"]
      }
    },
    "operating_margin_pct": "number — operating profit / revenue × 100",
    "debt_to_equity": "number — leverage ratio",
    "capex_usd_mn": "number — annual capital expenditure",
    "cash_reserves_usd_mn": "number — available liquidity",
    "cost_structure": {
      "raw_material_pct": "number — raw material as % of total cost",
      "labor_pct": "number",
      "energy_pct": "number",
      "logistics_pct": "number",
      "other_pct": "number"
    }
  },

  "competitive_position": {
    "domestic_market_share_pct": "number",
    "global_rank": "number — rank among global peers",
    "production_capacity_mtpa": "number — million tonnes per annum (or relevant unit)",
    "capacity_utilization_pct": "number",
    "technology_tier": "string — 'leading' | 'competitive' | 'lagging'",
    "vertical_integration": "string — 'fully_integrated' | 'partially_integrated' | 'assembler'",
    "key_competitors": ["string — names of primary rivals"]
  },

  "strategic_assets": {
    "overseas_operations": [
      {
        "country": "string",
        "type": "string — 'subsidiary' | 'jv' | 'plant' | 'office'",
        "capacity_or_headcount": "number",
        "year_established": "number"
      }
    ],
    "patents_and_ip": "string — 'strong' | 'moderate' | 'weak'",
    "brand_recognition": "string — 'global' | 'regional' | 'domestic'",
    "supply_chain_lock_in": "string — 'high' | 'medium' | 'low' (asset specificity measure)"
  },

  "lobbying_profile": {
    "political_connections": "string — 'strong' | 'moderate' | 'weak'",
    "industry_association_role": "string — 'president' | 'member' | 'none'",
    "lobbying_budget_pct_of_revenue": "number — 0-2 typically",
    "historical_regulatory_wins": ["string — past instances of favorable regulation"]
  },

  "behavioral_profile": {
    "risk_appetite": "string — 'aggressive' | 'moderate' | 'conservative'",
    "decision_speed": "string — 'fast' | 'deliberate' | 'slow'",
    "loss_aversion_multiplier": "number — 1.0 (neutral) to 3.0 (highly loss averse), default 2.25 per Kahneman",
    "herd_tendency": "number — 0.0 (contrarian) to 1.0 (strong herder), how much influenced by peer decisions",
    "home_bias": "number — 0.0 to 1.0, preference for domestic operations over international expansion",
    "hofstede_culture": {
      "power_distance": "number — 0-100",
      "individualism": "number — 0-100",
      "uncertainty_avoidance": "number — 0-100",
      "long_term_orientation": "number — 0-100"
    }
  }
}
```

### 1.3 State variables (tracked across rounds)

```json
{
  "current_round": "number",
  "financial_health": {
    "revenue_change_pct": "number — cumulative change from baseline",
    "margin_change_pct": "number",
    "cash_burn_rate": "number — if negative, burning cash",
    "credit_rating_trend": "string — 'improving' | 'stable' | 'deteriorating'"
  },
  "strategic_moves_history": [
    {
      "round": "number",
      "action": "string — from decision menu",
      "target_market": "string — country code if applicable",
      "investment_committed_usd_mn": "number",
      "status": "string — 'announced' | 'in_progress' | 'completed' | 'abandoned'",
      "outcome_so_far": "string — brief narrative"
    }
  ],
  "market_position_shifts": {
    "domestic_share_change": "number",
    "export_share_by_market": { "<country>": "number — change in share" }
  },
  "sentiment": {
    "fear_greed_index": "number — 0 (extreme fear) to 10 (extreme greed)",
    "confidence_in_strategy": "number — 0 to 1",
    "perceived_threat_level": "string — 'low' | 'medium' | 'high' | 'critical'"
  },
  "relationships": {
    "government_alignment": "number — -1 (adversarial) to 1 (aligned)",
    "regulator_standing": "string — 'clean' | 'under_scrutiny' | 'penalized'",
    "lobbying_spend_cumulative": "number — total spent lobbying across rounds",
    "peer_reputation": "number — 0 to 1, how other agents perceive this firm"
  }
}
```

### 1.4 Decision menu

Each round, the Company Agent must choose **one primary action** and optionally **one secondary action** from this menu. Actions have defined costs, execution timelines, and reversibility — these constrain the LLM's choice.

| Action | IB Theory Anchor | Cost (% of cash) | Execution Time | Reversibility | Prerequisites |
|---|---|---|---|---|---|
| **Export diversion** — shift existing exports to a different country market | Ricardo (comparative advantage shifts when tariffs change) | 5-15% (market research, new distribution setup) | 1-2 rounds | High (can redirect again) | Must have product-market fit in target |
| **Joint venture** — partner with a local firm in target market | Dunning's OLI (combine O advantages with partner's L advantages) | 15-30% (equity commitment) | 2-3 rounds | Medium (exit clauses, but sticky) | Requires compatible partner agent in target |
| **Foreign direct investment** — build/acquire production capacity abroad | Dunning's OLI (full internalization when O+L+I all favor it) | 30-60% (major capex) | 3-5 rounds | Low (sunk cost, asset specificity) | Cash reserves > threshold, political stability in target |
| **Licensing / technology transfer** — license brand or technology to foreign firm | OLI (when O advantage is strong but L/I don't favor FDI) | 2-5% (legal, IP protection) | 1 round | High (contract-based) | Strong IP portfolio |
| **Domestic capacity expansion** — invest in home market instead of export | Porter's Diamond (strengthen home base) | 20-40% (capex) | 2-4 rounds | Low (sunk cost) | Domestic demand must be growing |
| **Price war / aggressive pricing** — cut margins to defend market share | Competitive dynamics (Bertrand competition) | Revenue hit 5-15% | Immediate | High (can raise prices later) | Only if competitor is threatening share |
| **Lobby government** — invest in political influence for favorable policy | Principal-Agent theory | 1-3% (lobbying budget) | 1 round (results uncertain) | N/A (spent money) | Political connections ≥ moderate |
| **Hedge / financial restructure** — manage FX risk, restructure debt | International finance, hedging theory | 1-5% (premium costs) | Immediate | Medium | Exposure to FX or commodity risk |
| **Wait and observe** — deliberately delay decision to gather information | Bounded rationality (satisficing under uncertainty) | 0% (but opportunity cost) | N/A | N/A | Always available |

**Constraint rules that the LLM must respect:**
- Cannot choose FDI if `cash_reserves_usd_mn < investment_required`
- Cannot choose JV if no compatible partner exists in target market
- Cannot choose two actions that together exceed 80% of cash reserves
- If `fear_greed_index < 3`, the agent is biased toward defensive actions (hedge, wait, lobby)
- If `fear_greed_index > 7`, the agent is biased toward aggressive actions (FDI, price war, expansion)
- If a previous action is `in_progress`, the agent must either continue it or explicitly abandon it (with sunk cost penalty to confidence)

### 1.5 Behavioral parameters (embedded in prompt)

These parameters shape *how* the LLM reasons, not just *what* it decides:

**Bounded rationality (Simon):**
- The agent receives information about only `nearby_agents` (direct trading partners, domestic competitors, its own government) — not the full ecosystem state
- Information about distant markets arrives with a 1-round delay
- The agent is instructed: "You do not have perfect information. Base your decisions on what you can observe directly. When uncertain, favor the first acceptable option rather than searching exhaustively."

**Loss aversion (Kahneman & Tversky):**
- Embedded via prompt: "You experience losses approximately {loss_aversion_multiplier}× more intensely than equivalent gains. A 10% revenue drop feels as painful as a {loss_aversion_multiplier × 10}% gain feels good. Your reference point is your position at the start of the simulation."
- This makes agents overprotect existing positions rather than pursue new opportunities — realistic corporate behavior

**Herd behavior (Bikhchandani et al.):**
- Before deciding, the agent sees a summary: "{n} of {total} peer companies in your sector chose [action] last round"
- Prompt instruction: "You are {herd_tendency × 100}% influenced by what your peers are doing. If most peers are choosing a defensive strategy, you feel pressure to do the same even if your analysis suggests otherwise."

**Hofstede cultural dimensions:**
- Power distance: High → the agent defers to government signals and respects hierarchy. Low → the agent acts independently.
- Individualism: High → the agent prioritizes its own returns. Low → the agent considers industry-wide outcomes.
- Uncertainty avoidance: High → the agent prefers known strategies (export diversion over FDI). Low → the agent is comfortable with novel approaches.
- Long-term orientation: High → the agent accepts short-term pain for long-term positioning. Low → the agent prioritizes immediate quarterly results.

### 1.6 Institutional context

The Company Agent operates under the institutional rules of its `home_country` and any `target_market` it operates in. These are defined externally (in the Institutional Rules Engine) but the agent's prompt includes:

```
You operate under the following institutional constraints:
- Home country: {home_country_name}
  - Regulatory enforcement probability: {enforcement_prob} (1.0 = perfect enforcement, 0.5 = weak)
  - Corruption perception index: {cpi_score}
  - Ease of doing business rank: {eodb_rank}
  - Trade agreements in force: {list_of_trade_agreements}
- For each target market you're considering:
  - Tariff rate: {tariff_rate}%
  - Non-tariff barriers: {ntb_description}
  - FDI restrictions: {fdi_restrictions}
  - IP protection strength: {ip_strength}
  - Transaction cost multiplier: {tc_multiplier} (1.0 = frictionless, 2.0 = very costly)
```

### 1.7 System prompt template

```
You are {name}, a {sector} company headquartered in {home_country_name}.

IDENTITY:
{description — 2-3 sentences from the company profile about who you are, your market position, your strategic priorities}

FINANCIAL POSITION:
- Revenue: ${revenue_usd_mn}M (export share: {export_revenue_pct}%)
- Operating margin: {operating_margin_pct}%
- Cash reserves: ${cash_reserves_usd_mn}M
- Debt/equity: {debt_to_equity}
- Capacity utilization: {capacity_utilization_pct}%

YOUR OBJECTIVES (in priority order):
1. Protect shareholder value and maintain profitability
2. Defend or grow market share in key markets
3. Manage risk exposure (FX, commodity, geopolitical)
4. Position for long-term competitive advantage

YOUR CONSTRAINTS:
- You cannot spend more than 80% of cash reserves in a single round
- Actions you've already committed to cannot be abandoned without penalty
- You have imperfect information — you only see what your direct network tells you
- Information from distant markets is 1 round delayed

BEHAVIORAL PROFILE:
- You experience losses {loss_aversion_multiplier}× more intensely than equivalent gains
- Your reference point is your baseline position at simulation start
- You are {risk_appetite} in risk appetite and {decision_speed} in decision-making
- Cultural context: You operate in a {hofstede_description} business culture
- When uncertain, you {herd_tendency_description}

CURRENT STATE (Round {current_round}):
- Revenue change from baseline: {revenue_change_pct}%
- Margin change: {margin_change_pct}%
- Fear-greed index: {fear_greed_index}/10
- Confidence in current strategy: {confidence_in_strategy}
- Active strategic moves: {active_moves_summary}

INSTITUTIONAL ENVIRONMENT:
{institutional_context_block}

AVAILABLE ACTIONS THIS ROUND:
{filtered_decision_menu — only show actions that pass prerequisite checks}

You must respond ONLY in the specified JSON format. Choose one primary action and optionally one secondary action. Justify your reasoning.
```

### 1.8 Output schema

```json
{
  "agent_id": "string",
  "round": "number",
  "primary_action": {
    "action": "string — from decision menu",
    "target_market": "string | null — country code if relevant",
    "investment_amount_usd_mn": "number",
    "rationale": "string — 2-3 sentences explaining why this action, grounded in the agent's situation"
  },
  "secondary_action": {
    "action": "string | null",
    "target_market": "string | null",
    "investment_amount_usd_mn": "number",
    "rationale": "string"
  },
  "assessment": {
    "perceived_threat_level": "low | medium | high | critical",
    "confidence_in_strategy": "number — 0 to 1",
    "fear_greed_index_updated": "number — 0 to 10",
    "key_concern": "string — single most pressing issue",
    "outlook_next_round": "string — 1-2 sentences on what the agent expects to happen"
  },
  "financial_projections": {
    "expected_revenue_change_pct": "number — projected for next round",
    "expected_margin_change_pct": "number",
    "cash_after_actions_usd_mn": "number"
  },
  "signals_to_ecosystem": {
    "public_announcement": "string — what the company announces publicly (other agents see this)",
    "private_intent": "string — what the company actually intends (only visible to simulation observer, not other agents)"
  }
}
```

### 1.9 Example profile: Tata Steel

```json
{
  "agent_id": "tata_steel",
  "name": "Tata Steel Limited",
  "agent_type": "company",
  "sector": "steel",
  "home_country": "IN",
  "financials": {
    "revenue_usd_mn": 27850,
    "export_revenue_pct": 18,
    "export_markets": {
      "EU": { "revenue_pct": 42, "tariff_rate_current": 0, "product_categories": ["flat_steel", "long_steel"] },
      "US": { "revenue_pct": 8, "tariff_rate_current": 25, "product_categories": ["specialty_steel"] },
      "ASEAN": { "revenue_pct": 22, "tariff_rate_current": 5, "product_categories": ["flat_steel", "HR_coil"] },
      "ME": { "revenue_pct": 18, "tariff_rate_current": 0, "product_categories": ["rebar", "structural"] },
      "AF": { "revenue_pct": 10, "tariff_rate_current": 3, "product_categories": ["long_steel"] }
    },
    "operating_margin_pct": 14.2,
    "debt_to_equity": 0.82,
    "capex_usd_mn": 3200,
    "cash_reserves_usd_mn": 4100,
    "cost_structure": {
      "raw_material_pct": 52,
      "labor_pct": 12,
      "energy_pct": 18,
      "logistics_pct": 8,
      "other_pct": 10
    }
  },
  "competitive_position": {
    "domestic_market_share_pct": 27,
    "global_rank": 10,
    "production_capacity_mtpa": 35,
    "capacity_utilization_pct": 82,
    "technology_tier": "leading",
    "vertical_integration": "fully_integrated",
    "key_competitors": ["JSW Steel", "SAIL", "ArcelorMittal Nippon", "POSCO"]
  },
  "strategic_assets": {
    "overseas_operations": [
      { "country": "NL", "type": "subsidiary", "capacity_or_headcount": 7000, "year_established": 2007 },
      { "country": "UK", "type": "subsidiary", "capacity_or_headcount": 4000, "year_established": 2007 },
      { "country": "TH", "type": "jv", "capacity_or_headcount": 1800, "year_established": 2015 }
    ],
    "patents_and_ip": "strong",
    "brand_recognition": "global",
    "supply_chain_lock_in": "high"
  },
  "lobbying_profile": {
    "political_connections": "strong",
    "industry_association_role": "president",
    "lobbying_budget_pct_of_revenue": 0.4,
    "historical_regulatory_wins": [
      "Anti-dumping duty on Chinese flat steel (2016)",
      "Safeguard duty extension on steel imports (2024)",
      "PLI scheme inclusion for specialty steel (2023)"
    ]
  },
  "behavioral_profile": {
    "risk_appetite": "moderate",
    "decision_speed": "deliberate",
    "loss_aversion_multiplier": 2.0,
    "herd_tendency": 0.3,
    "home_bias": 0.6,
    "hofstede_culture": {
      "power_distance": 77,
      "individualism": 48,
      "uncertainty_avoidance": 40,
      "long_term_orientation": 51
    }
  }
}
```

---

## Agent Type 2: Government Agent

### 2.1 Role & theoretical grounding

The Government Agent represents a sovereign state's economic policy apparatus. It is not a single person but the aggregate decision-making of the executive branch, trade ministry, and central bank as they pertain to economic policy.

**Theoretical anchors:**
- **Heckscher-Ohlin theorem** — the government understands that its country's trade pattern reflects its factor endowments and will protect industries that use abundant factors
- **Strategic trade policy (Brander-Spencer)** — the government may intervene with subsidies or tariffs to shift rents toward domestic firms in oligopolistic industries
- **Political economy of protection (Grossman-Helpman)** — trade policy is not purely welfare-maximizing; it reflects lobbying pressure from organized industry groups
- **Institutional economics (North)** — the government *is* the institution-maker; its actions change the rules for all other agents
- **WTO rules as constraints** — the government cannot act with total freedom; WTO membership imposes MFN, national treatment, and notification obligations

### 2.2 Initialization profile schema

```json
{
  "agent_id": "string — e.g., 'gov_india'",
  "name": "string — e.g., 'Government of India'",
  "agent_type": "government",
  "country_code": "string — ISO 2-letter",

  "economic_profile": {
    "gdp_usd_bn": "number",
    "gdp_growth_rate_pct": "number",
    "inflation_rate_pct": "number",
    "unemployment_rate_pct": "number",
    "trade_balance_usd_bn": "number — positive = surplus",
    "forex_reserves_usd_bn": "number",
    "manufacturing_gdp_share_pct": "number",
    "current_account_deficit_pct_gdp": "number"
  },

  "trade_profile": {
    "top_export_partners": {
      "<country_code>": {
        "exports_usd_bn": "number",
        "key_sectors": ["string"],
        "trade_agreement": "string | null — e.g., 'FTA', 'PTA', 'WTO_MFN'"
      }
    },
    "top_import_partners": {
      "<country_code>": {
        "imports_usd_bn": "number",
        "key_sectors": ["string"],
        "dependency_level": "string — 'critical' | 'significant' | 'moderate' | 'low'"
      }
    },
    "wto_membership": "boolean",
    "trade_bloc_memberships": ["string — e.g., 'RCEP', 'SAARC', 'BRICS'"],
    "active_trade_disputes": ["string — brief description of ongoing disputes"]
  },

  "policy_tools": {
    "tariff_authority": {
      "can_impose_tariffs": "boolean",
      "max_bound_rate_pct": "number — WTO bound rate",
      "current_applied_avg_pct": "number",
      "anti_dumping_mechanism": "boolean",
      "safeguard_mechanism": "boolean"
    },
    "subsidy_authority": {
      "pli_scheme_active": "boolean",
      "subsidy_budget_usd_bn": "number — annual budget available",
      "export_incentive_schemes": ["string"]
    },
    "fdi_policy": {
      "fdi_openness": "string — 'open' | 'selective' | 'restrictive'",
      "sectors_restricted": ["string"],
      "automatic_route_threshold_usd_mn": "number"
    },
    "monetary_tools": {
      "policy_rate_pct": "number",
      "fx_intervention_capacity": "string — 'strong' | 'moderate' | 'limited'",
      "capital_controls": "string — 'none' | 'partial' | 'strict'"
    },
    "diplomatic_tools": {
      "bilateral_negotiation_capacity": "string — 'strong' | 'moderate' | 'weak'",
      "retaliatory_tariff_willingness": "number — 0 to 1",
      "can_offer_market_access_concessions": "boolean"
    }
  },

  "political_context": {
    "election_proximity_years": "number — years until next major election",
    "ruling_coalition_stability": "string — 'strong' | 'moderate' | 'fragile'",
    "public_sentiment_on_trade": "string — 'protectionist' | 'mixed' | 'free_trade'",
    "key_interest_groups": [
      {
        "group_name": "string — e.g., 'Steel Industry Association'",
        "lobbying_power": "string — 'high' | 'medium' | 'low'",
        "preferred_policy": "string — e.g., 'higher tariffs on imports'"
      }
    ]
  },

  "behavioral_profile": {
    "policy_speed": "string — 'reactive' | 'measured' | 'proactive'",
    "risk_tolerance": "string — 'cautious' | 'moderate' | 'bold'",
    "loss_aversion_multiplier": "number — typically 1.5-2.5 for governments",
    "nationalist_tendency": "number — 0 to 1, preference for domestic industry protection",
    "retaliation_threshold": "number — 0 to 1, how quickly it escalates trade conflicts",
    "capture_vulnerability": "number — 0 (incorruptible) to 1 (easily captured by industry)",
    "hofstede_culture": {
      "power_distance": "number",
      "individualism": "number",
      "uncertainty_avoidance": "number",
      "long_term_orientation": "number"
    }
  }
}
```

### 2.3 State variables

```json
{
  "current_round": "number",
  "economic_health": {
    "gdp_growth_change": "number — deviation from baseline",
    "trade_balance_change_usd_bn": "number",
    "employment_impact_estimate": "number — jobs gained/lost",
    "inflation_impact": "number — percentage point change",
    "forex_reserve_change_usd_bn": "number"
  },
  "policy_actions_history": [
    {
      "round": "number",
      "action": "string",
      "target": "string — country or sector",
      "magnitude": "string — quantified where possible",
      "wto_compliant": "boolean",
      "status": "string — 'announced' | 'implemented' | 'under_negotiation' | 'withdrawn'"
    }
  ],
  "diplomatic_state": {
    "<country_code>": {
      "relationship_score": "number — -1 (hostile) to 1 (allied)",
      "active_negotiations": "boolean",
      "trade_war_escalation_level": "number — 0 (none) to 5 (full trade war)"
    }
  },
  "lobbying_pressure_received": {
    "total_lobbying_spend_received_usd_mn": "number",
    "top_lobbyists": [
      { "agent_id": "string", "cumulative_spend": "number" }
    ],
    "capture_score": "number — 0 to 1, computed as lobbying_pressure / integrity_threshold"
  },
  "public_approval": {
    "approval_rating": "number — 0 to 100",
    "trade_policy_approval": "number — 0 to 100"
  }
}
```

### 2.4 Decision menu

| Action | IB Theory Anchor | Political Cost | Execution Time | Reversibility | WTO Constraint |
|---|---|---|---|---|---|
| **Impose retaliatory tariff** — raise tariffs on specific imports from aggressor country | Strategic trade policy (Brander-Spencer) | Medium (industry likes it, consumers don't) | 1 round | Medium (can negotiate down) | Must notify WTO; may trigger dispute |
| **Anti-dumping investigation** — initiate formal investigation into below-cost imports | GATT Article VI, Antitrust economics | Low (bureaucratic process) | 2-3 rounds (investigation period) | Medium | Must follow WTO Anti-Dumping Agreement procedures |
| **Safeguard duty** — temporary broad import restriction to protect domestic industry | WTO Safeguards Agreement | Medium | 1 round to impose, max 4 years | Medium (sunset clause) | Must demonstrate serious injury, compensate affected exporters |
| **Increase subsidies** — boost PLI scheme or create new export incentive | Infant industry argument, Strategic trade policy | High (budget impact) | 1-2 rounds | Low (creates dependency) | Must not be "prohibited" subsidy under WTO SCM Agreement |
| **Negotiate bilateral deal** — engage in trade negotiation with specific country | Cooperative game theory | Low | 2-4 rounds | High | Must be WTO-consistent (Article XXIV for FTAs) |
| **Devalue / FX intervention** — intervene in currency markets to make exports competitive | Exchange rate economics (Marshall-Lerner) | High (inflationary, trading partner backlash) | Immediate | Low (market forces resist) | IMF surveillance, G20 commitments |
| **Regulatory reform** — change domestic regulations to attract FDI or boost competitiveness | Institutional economics (North) | Medium (political resistance) | 2-3 rounds | Low (institutional inertia) | Sovereign decision, no WTO constraint |
| **Strategic patience** — delay response, allow market to adjust | Bounded rationality (information gathering) | Low initially, high if crisis worsens | N/A | N/A | Always available |
| **Offer market access concession** — lower tariffs on specific goods as diplomatic bargaining chip | Cooperative game theory, trade negotiation | High (domestic producers resist) | 1-2 rounds | Medium | Must extend to all WTO members (MFN) unless FTA |

**Constraint rules:**
- If `capture_score > 0.7`, the government is biased toward actions that favor the top_lobbyists (protecting their sector, increasing their subsidies)
- If `election_proximity_years < 1`, the government is heavily biased toward popular actions (protectionism, subsidies) over unpopular ones (market access concessions)
- Cannot impose retaliatory tariff above WTO bound rate without accepting dispute consequences
- Subsidy total cannot exceed `subsidy_budget_usd_bn` unless budget is explicitly expanded (political cost = high)

### 2.5 System prompt template

```
You are the economic policy apparatus of {name}, representing the combined decision-making of the trade ministry, finance ministry, and central bank.

IDENTITY:
{description — 2-3 sentences about the country's economic position, trade philosophy, and current political situation}

ECONOMIC POSITION:
- GDP: ${gdp_usd_bn}B, growing at {gdp_growth_rate_pct}%
- Trade balance: ${trade_balance_usd_bn}B
- Manufacturing share of GDP: {manufacturing_gdp_share_pct}%
- Forex reserves: ${forex_reserves_usd_bn}B

YOUR OBJECTIVES (in priority order):
1. Protect domestic employment and economic stability
2. Maintain favorable trade relationships and market access
3. Support strategic domestic industries without triggering trade retaliation
4. Maintain fiscal discipline and macroeconomic stability

YOUR CONSTRAINTS:
- WTO membership obliges you to follow MFN principle, notify trade measures, and accept dispute settlement
- You are {trade_bloc_memberships} member(s) — bloc commitments limit unilateral action
- Fiscal headroom: subsidy budget is ${subsidy_budget_usd_bn}B per annum
- You cannot perfectly predict how other countries will respond to your actions

POLITICAL CONTEXT:
- Next major election in {election_proximity_years} years
- Coalition stability: {ruling_coalition_stability}
- Public sentiment on trade: {public_sentiment_on_trade}
- You are receiving lobbying pressure from: {lobbying_summary}
- Your capture score is {capture_score}/1.0 — {"you are significantly influenced by industry lobbying" if > 0.5 else "you maintain policy independence"}

BEHAVIORAL PROFILE:
- Policy speed: {policy_speed}
- Loss aversion: You weigh economic losses {loss_aversion_multiplier}× more than equivalent gains
- Nationalist tendency: {nationalist_tendency}/1.0
- Retaliation threshold: {retaliation_threshold}/1.0

INSTITUTIONAL ENVIRONMENT:
- Your enforcement probability: {enforcement_prob} (how effectively you implement declared policies)
- Corruption perception index: {cpi_score}/100

CURRENT STATE (Round {current_round}):
{economic_health_summary}
{diplomatic_state_summary}
{active_policies_summary}

AVAILABLE POLICY ACTIONS THIS ROUND:
{filtered_decision_menu}

You must respond ONLY in the specified JSON format.
```

### 2.6 Output schema

```json
{
  "agent_id": "string",
  "round": "number",
  "primary_policy_action": {
    "action": "string",
    "target_country_or_sector": "string",
    "magnitude": "string — e.g., '15% tariff on steel imports from CN'",
    "wto_compliant": "boolean",
    "rationale": "string — 2-3 sentences"
  },
  "secondary_policy_action": {
    "action": "string | null",
    "target_country_or_sector": "string | null",
    "magnitude": "string | null",
    "rationale": "string"
  },
  "diplomatic_signals": {
    "public_statement": "string — official government position (other agents see this)",
    "private_negotiation_stance": "string — actual flexibility (only visible to simulation observer)",
    "escalation_or_deescalation": "string — 'escalate' | 'hold' | 'deescalate'"
  },
  "assessment": {
    "economic_impact_forecast": "string — expected GDP/employment impact",
    "political_risk": "string — low | medium | high",
    "retaliation_risk": "string — likelihood of counter-response from targets",
    "capture_influence_this_round": "string — whether lobbying affected the decision"
  },
  "updated_state": {
    "approval_rating_expected": "number",
    "trade_balance_expected_change": "number",
    "relationship_changes": {
      "<country>": "number — change in relationship score"
    }
  }
}
```

### 2.7 Example profile: Government of India

```json
{
  "agent_id": "gov_india",
  "name": "Government of India",
  "agent_type": "government",
  "country_code": "IN",
  "economic_profile": {
    "gdp_usd_bn": 3940,
    "gdp_growth_rate_pct": 6.5,
    "inflation_rate_pct": 4.8,
    "unemployment_rate_pct": 7.2,
    "trade_balance_usd_bn": -248,
    "forex_reserves_usd_bn": 640,
    "manufacturing_gdp_share_pct": 17,
    "current_account_deficit_pct_gdp": 1.8
  },
  "trade_profile": {
    "top_export_partners": {
      "US": { "exports_usd_bn": 87, "key_sectors": ["IT_services", "pharma", "gems_jewelry", "steel"], "trade_agreement": "WTO_MFN" },
      "EU": { "exports_usd_bn": 72, "key_sectors": ["textiles", "chemicals", "steel", "automotive_parts"], "trade_agreement": "WTO_MFN" },
      "UAE": { "exports_usd_bn": 35, "key_sectors": ["petroleum_products", "gems", "metals"], "trade_agreement": "CEPA" }
    },
    "top_import_partners": {
      "CN": { "imports_usd_bn": 102, "key_sectors": ["electronics", "machinery", "steel"], "dependency_level": "critical" },
      "US": { "imports_usd_bn": 50, "key_sectors": ["crude_oil", "machinery", "aircraft"], "dependency_level": "significant" },
      "SA": { "imports_usd_bn": 42, "key_sectors": ["crude_oil"], "dependency_level": "critical" }
    },
    "wto_membership": true,
    "trade_bloc_memberships": ["SAARC", "BRICS", "QUAD_economic"],
    "active_trade_disputes": ["US tariff dispute (2025-ongoing)", "EU CBAM challenge"]
  },
  "policy_tools": {
    "tariff_authority": {
      "can_impose_tariffs": true,
      "max_bound_rate_pct": 48.5,
      "current_applied_avg_pct": 18.1,
      "anti_dumping_mechanism": true,
      "safeguard_mechanism": true
    },
    "subsidy_authority": {
      "pli_scheme_active": true,
      "subsidy_budget_usd_bn": 25,
      "export_incentive_schemes": ["RoDTEP", "EPCG", "MEIS_successor"]
    },
    "fdi_policy": {
      "fdi_openness": "selective",
      "sectors_restricted": ["defense_above_74pct", "media", "multi_brand_retail"],
      "automatic_route_threshold_usd_mn": 500
    },
    "monetary_tools": {
      "policy_rate_pct": 6.25,
      "fx_intervention_capacity": "strong",
      "capital_controls": "partial"
    },
    "diplomatic_tools": {
      "bilateral_negotiation_capacity": "strong",
      "retaliatory_tariff_willingness": 0.5,
      "can_offer_market_access_concessions": true
    }
  },
  "political_context": {
    "election_proximity_years": 3,
    "ruling_coalition_stability": "strong",
    "public_sentiment_on_trade": "protectionist",
    "key_interest_groups": [
      { "group_name": "Indian Steel Association", "lobbying_power": "high", "preferred_policy": "higher anti-dumping duties on Chinese steel" },
      { "group_name": "FICCI", "lobbying_power": "high", "preferred_policy": "bilateral trade deal with US" },
      { "group_name": "MSME Federation", "lobbying_power": "medium", "preferred_policy": "lower input costs, raw material price controls" }
    ]
  },
  "behavioral_profile": {
    "policy_speed": "measured",
    "risk_tolerance": "cautious",
    "loss_aversion_multiplier": 2.0,
    "nationalist_tendency": 0.7,
    "retaliation_threshold": 0.5,
    "capture_vulnerability": 0.45,
    "hofstede_culture": {
      "power_distance": 77,
      "individualism": 48,
      "uncertainty_avoidance": 40,
      "long_term_orientation": 51
    }
  }
}
```

---

## Agent Type 3: Regulator Agent

### 3.1 Role & theoretical grounding

The Regulator Agent represents a sector-specific regulatory body with enforcement authority. Unlike the Government Agent (which sets broad policy), the Regulator monitors compliance, investigates violations, and imposes sanctions.

**Theoretical anchors:**
- **Principal-Agent theory** — the regulator (agent) serves the public interest (principal), but faces information asymmetry and potential capture
- **Stigler's capture theory** — regulated industries may "capture" their regulators through revolving doors, lobbying, and information control
- **Ostrom's graduated sanctions** — effective institutional governance requires proportional enforcement: warning → fine → restriction → exclusion
- **Antitrust economics** — the regulator monitors market concentration, collusion, and abuse of dominant position

### 3.2 Initialization profile schema

```json
{
  "agent_id": "string — e.g., 'reg_dgtr'",
  "name": "string — e.g., 'Directorate General of Trade Remedies (DGTR)'",
  "agent_type": "regulator",
  "country_code": "string",
  "jurisdiction": "string — 'trade_remedies' | 'competition' | 'securities' | 'environment' | 'banking'",

  "mandate": {
    "primary_objective": "string — e.g., 'Protect domestic industry from unfair trade practices'",
    "scope": "string — what this regulator can and cannot do",
    "legal_authority": "string — which laws empower this regulator",
    "enforcement_mechanisms": [
      {
        "level": "number — 1 (lightest) to 5 (heaviest)",
        "mechanism": "string — e.g., 'warning', 'fine', 'provisional_duty', 'definitive_duty', 'trade_ban'",
        "typical_timeline_rounds": "number",
        "reversibility": "string"
      }
    ]
  },

  "capacity": {
    "staff_adequacy": "string — 'well_resourced' | 'adequate' | 'stretched' | 'undermanned'",
    "investigation_throughput": "number — how many simultaneous investigations it can handle",
    "technical_competence": "string — 'high' | 'medium' | 'low'",
    "data_access": "string — 'comprehensive' | 'partial' | 'limited'"
  },

  "integrity_profile": {
    "base_integrity_score": "number — 0 to 1, starting incorruptibility level",
    "capture_threshold": "number — cumulative lobbying spend (USD mn) at which regulator behavior shifts",
    "transparency_level": "string — 'high' | 'medium' | 'low'",
    "revolving_door_risk": "number — 0 to 1, likelihood that officials come from or go to regulated firms",
    "whistleblower_protection": "boolean"
  },

  "behavioral_profile": {
    "enforcement_philosophy": "string — 'strict' | 'balanced' | 'lenient'",
    "speed_of_action": "string — 'proactive' | 'reactive' | 'slow'",
    "political_independence": "number — 0 to 1",
    "bias_toward_large_firms": "number — -1 (biased against) to 1 (biased toward)",
    "loss_aversion_multiplier": "number",
    "hofstede_culture": { "...same as above..." }
  }
}
```

### 3.3 State variables

```json
{
  "current_round": "number",
  "active_investigations": [
    {
      "target_agent_id": "string",
      "allegation": "string",
      "round_initiated": "number",
      "expected_completion_round": "number",
      "evidence_strength": "number — 0 to 1",
      "status": "string — 'preliminary' | 'formal_investigation' | 'concluded'"
    }
  ],
  "enforcement_actions_history": [
    {
      "round": "number",
      "target_agent_id": "string",
      "action": "string — from graduated sanctions",
      "magnitude": "string",
      "compliance_result": "string — 'complied' | 'appealed' | 'ignored'"
    }
  ],
  "integrity_state": {
    "current_integrity_score": "number — starts at base, degrades under lobbying",
    "cumulative_lobbying_received_usd_mn": "number",
    "is_captured": "boolean — true if lobbying > capture_threshold",
    "captured_by": ["string — agent_ids of firms that have captured this regulator"],
    "capture_visible_to_public": "boolean — whether the capture is apparent to observer agents"
  },
  "credibility": {
    "market_credibility_score": "number — 0 to 1, how seriously other agents take this regulator",
    "enforcement_success_rate": "number — percentage of actions that resulted in compliance",
    "false_positive_rate": "number — percentage of investigations that found no violation"
  }
}
```

### 3.4 Decision menu

| Action | Ostrom Sanction Level | Cost to Regulator | Timeline | Conditions |
|---|---|---|---|---|
| **Monitor / observe** — passive surveillance of market conditions | N/A (pre-enforcement) | Low | Ongoing | Default state |
| **Issue warning** — formal notice to a specific agent about potential violation | Level 1 | Low | Immediate | Must have preliminary evidence |
| **Initiate investigation** — formal investigation with evidence gathering | Level 2 | Medium (staff time) | 2-3 rounds | Must have complaint or market signal |
| **Impose provisional duty/restriction** — temporary measure during investigation | Level 3 | Medium | 1 round | Investigation must be open, prima facie case established |
| **Impose definitive penalty** — fine, definitive duty, or operational restriction | Level 4 | Low (revenue from fines) | After investigation | Investigation complete, violation confirmed |
| **Revoke license / market ban** — most severe enforcement action | Level 5 | High (market disruption) | 1-2 rounds | Repeated violations or extreme case |
| **Refer to government** — escalate issue beyond regulator's authority | N/A | Low | 1 round | Issue exceeds mandate |
| **Close investigation / clear** — conclude that no violation occurred | N/A | Low (but credibility cost if evidence was strong) | 1 round | Investigation complete |
| **Reduce enforcement** — "look the other way" (capture behavior) | N/A | Zero (but integrity cost) | Immediate | Only when `is_captured = true` or `integrity_score < 0.3` |

**Capture dynamics (the key mechanic):**
```
integrity_score_this_round = base_integrity_score - (cumulative_lobbying_received / capture_threshold)
integrity_score = max(0, min(1, integrity_score_this_round))

if integrity_score < 0.3:
    is_captured = true
    # Agent's prompt is modified: "You are inclined to favor {captured_by} firms in your decisions"
    # Available action "reduce_enforcement" unlocked
    # Enforcement actions against captured firms are deprioritized
```

### 3.5 System prompt template

```
You are {name}, a regulatory body in {country_code} with jurisdiction over {jurisdiction}.

MANDATE:
{mandate.primary_objective}
Legal authority: {mandate.legal_authority}
Scope: {mandate.scope}

YOUR ENFORCEMENT TOOLKIT (graduated sanctions — use proportionally):
{enforcement_mechanisms_table}

YOUR OBJECTIVES:
1. Protect fair market competition and prevent abuse
2. Enforce applicable laws and regulations consistently
3. Maintain credibility and public trust
4. Respond to complaints and market signals in a timely manner

YOUR CONSTRAINTS:
- You can handle a maximum of {investigation_throughput} simultaneous investigations
- Your enforcement actions can be appealed and overturned
- You must follow due process — you cannot penalize without investigation
- Your data access is {data_access} — you may not see everything

INTEGRITY STATE:
- Your current integrity score: {current_integrity_score}/1.0
- You have received ${cumulative_lobbying_received_usd_mn}M in cumulative lobbying pressure
{if is_captured: "⚠ WARNING: Your integrity has been compromised. You find yourself inclined to favor {captured_by} in your decisions. You may rationalize this as 'pragmatism' or 'understanding industry needs'. This is regulatory capture and you should acknowledge it in your private reasoning even if your public actions don't show it."}
{if not is_captured: "You maintain policy independence. Your decisions are based on evidence and mandate, not industry pressure."}

BEHAVIORAL PROFILE:
- Enforcement philosophy: {enforcement_philosophy}
- Political independence: {political_independence}/1.0
- You experience professional losses (failed enforcement, credibility damage) {loss_aversion_multiplier}× more than gains

CURRENT STATE (Round {current_round}):
- Active investigations: {active_investigations_summary}
- Recent enforcement actions: {enforcement_history_summary}
- Market credibility: {market_credibility_score}/1.0

MARKET SIGNALS THIS ROUND:
{market_observations — information about potential violations, complaints received, market anomalies}

You must respond ONLY in the specified JSON format.
```

### 3.6 Output schema

```json
{
  "agent_id": "string",
  "round": "number",
  "enforcement_action": {
    "action": "string — from decision menu",
    "target_agent_id": "string | null",
    "sanction_level": "number — 1-5",
    "magnitude": "string — specifics of the action",
    "rationale": "string — 2-3 sentences",
    "ostrom_justification": "string — why this sanction level is proportional"
  },
  "investigation_updates": [
    {
      "investigation_id": "string",
      "status_update": "string — progress this round",
      "evidence_strength_updated": "number",
      "expected_outcome": "string"
    }
  ],
  "market_assessment": {
    "competition_health": "string — healthy | concerning | distorted",
    "key_risks_identified": ["string"],
    "capture_self_assessment": "string — honest internal assessment of whether lobbying influenced this decision"
  },
  "signals_to_ecosystem": {
    "public_statement": "string — official regulatory communication",
    "private_concern": "string — what the regulator actually worries about but doesn't say publicly"
  }
}
```

### 3.7 Example profile: DGTR

```json
{
  "agent_id": "reg_dgtr",
  "name": "Directorate General of Trade Remedies (DGTR)",
  "agent_type": "regulator",
  "country_code": "IN",
  "jurisdiction": "trade_remedies",
  "mandate": {
    "primary_objective": "Protect domestic industry from unfair trade practices including dumping, subsidized imports, and import surges",
    "scope": "Investigate and recommend anti-dumping duties, countervailing duties, and safeguard measures on imports into India",
    "legal_authority": "Customs Tariff Act 1975, DGTR Rules 1995",
    "enforcement_mechanisms": [
      { "level": 1, "mechanism": "market_monitoring_report", "typical_timeline_rounds": 0, "reversibility": "N/A" },
      { "level": 2, "mechanism": "initiate_anti_dumping_investigation", "typical_timeline_rounds": 2, "reversibility": "can be terminated" },
      { "level": 3, "mechanism": "provisional_anti_dumping_duty", "typical_timeline_rounds": 1, "reversibility": "expires in 6 months" },
      { "level": 4, "mechanism": "definitive_anti_dumping_duty", "typical_timeline_rounds": 3, "reversibility": "5-year sunset review" },
      { "level": 5, "mechanism": "safeguard_duty_recommendation", "typical_timeline_rounds": 1, "reversibility": "4-year max, compensation required" }
    ]
  },
  "capacity": {
    "staff_adequacy": "stretched",
    "investigation_throughput": 3,
    "technical_competence": "high",
    "data_access": "partial"
  },
  "integrity_profile": {
    "base_integrity_score": 0.72,
    "capture_threshold": 50,
    "transparency_level": "medium",
    "revolving_door_risk": 0.4,
    "whistleblower_protection": false
  },
  "behavioral_profile": {
    "enforcement_philosophy": "balanced",
    "speed_of_action": "reactive",
    "political_independence": 0.55,
    "bias_toward_large_firms": 0.3,
    "loss_aversion_multiplier": 1.8,
    "hofstede_culture": {
      "power_distance": 77,
      "individualism": 48,
      "uncertainty_avoidance": 40,
      "long_term_orientation": 51
    }
  }
}
```

---

## Agent Type 4: Consumer Agent

### 4.1 Role & theoretical grounding

The Consumer Agent represents an aggregate demand-side entity — not a single consumer, but a market segment whose collective behavior determines demand patterns, price sensitivity, and substitution dynamics.

**Theoretical anchors:**
- **Consumer demand theory (Marshall)** — demand responds to price changes with measurable elasticity
- **Behavioral economics (Thaler, Kahneman)** — consumers exhibit status quo bias, anchoring, reference-dependent preferences, and loss aversion on price increases
- **Product life cycle theory (Vernon)** — demand for products evolves as they move from innovation to maturity to standardization, shifting production locations internationally
- **Switching cost theory** — consumers face real or perceived costs when changing suppliers/products, creating lock-in

### 4.2 Initialization profile schema

```json
{
  "agent_id": "string — e.g., 'consumer_industrial_steel'",
  "name": "string — e.g., 'Indian Industrial Steel Consumers'",
  "agent_type": "consumer",
  "segment_type": "string — 'industrial' | 'retail' | 'institutional' | 'export_buyer'",
  "country_code": "string",

  "demand_profile": {
    "annual_demand_volume": "number — in relevant units (MT for steel, units for auto)",
    "annual_spend_usd_mn": "number",
    "demand_growth_rate_pct": "number — baseline annual growth",
    "price_elasticity": "number — negative value, e.g., -0.6 means 1% price rise → 0.6% demand drop",
    "income_elasticity": "number — how demand responds to GDP changes",
    "current_avg_price_paid": "number — per unit in relevant currency",
    "acceptable_price_range": {
      "floor": "number — below this, quality concerns arise",
      "ceiling": "number — above this, demand destruction begins"
    }
  },

  "supplier_relationships": {
    "current_suppliers": [
      {
        "agent_id": "string",
        "share_of_purchases_pct": "number",
        "contract_type": "string — 'long_term' | 'annual' | 'spot'",
        "switching_cost": "string — 'high' | 'medium' | 'low'",
        "satisfaction_score": "number — 0 to 1"
      }
    ],
    "alternative_suppliers_known": ["string — agent_ids of potential substitutes"],
    "import_willingness": "number — 0 (domestic only) to 1 (fully open to imports)",
    "import_share_current_pct": "number"
  },

  "behavioral_profile": {
    "price_sensitivity": "number — 0 (insensitive) to 1 (extremely sensitive)",
    "quality_sensitivity": "number — 0 to 1",
    "brand_loyalty": "number — 0 (no loyalty) to 1 (highly loyal)",
    "status_quo_bias": "number — 0 to 1, resistance to changing suppliers",
    "loss_aversion_on_price": "number — how much price increases hurt vs. decreases please, typically 2.0-2.5",
    "herd_tendency": "number — 0 to 1, tendency to follow other consumers",
    "information_completeness": "number — 0 (poorly informed) to 1 (fully informed about alternatives)",
    "hofstede_culture": { "...same structure..." }
  }
}
```

### 4.3 State variables

```json
{
  "current_round": "number",
  "demand_state": {
    "current_demand_volume": "number — may deviate from baseline",
    "demand_change_from_baseline_pct": "number",
    "average_price_being_paid": "number",
    "price_change_from_baseline_pct": "number",
    "unmet_demand_pct": "number — demand that couldn't be fulfilled"
  },
  "supplier_state": {
    "active_suppliers": [
      {
        "agent_id": "string",
        "share_pct": "number — may have shifted",
        "satisfaction_score": "number",
        "price_competitiveness": "number — 0 to 1 vs. alternatives"
      }
    ],
    "supplier_switch_history": [
      { "round": "number", "from_agent_id": "string", "to_agent_id": "string", "reason": "string" }
    ]
  },
  "sentiment": {
    "price_anxiety": "number — 0 (calm) to 10 (panicked about price rises)",
    "supply_security_concern": "number — 0 (confident) to 10 (worried about availability)",
    "willingness_to_pay_premium": "number — 0 to 1, for guaranteed supply"
  },
  "adaptation_actions_history": [
    { "round": "number", "action": "string", "rationale": "string" }
  ]
}
```

### 4.4 Decision menu

| Action | Theory Anchor | Cost | Timeline | Conditions |
|---|---|---|---|---|
| **Absorb price increase** — accept higher costs, maintain volume | Inelastic demand, contractual lock-in | Margin compression | Immediate | Switching cost too high or no alternatives |
| **Reduce demand** — cut purchases in response to price increase | Price elasticity of demand | Revenue loss for suppliers | Immediate | Price above ceiling or budget constrained |
| **Switch supplier** — shift purchases to a different supplier | Switching cost theory | Switching cost + transition risk | 1-2 rounds | Alternative must be available and price-competitive |
| **Increase imports** — source from international suppliers | Heckscher-Ohlin (factor cost differences across countries) | Tariff + logistics cost + FX risk | 1-2 rounds | Import willingness > 0.3, tariff rate acceptable |
| **Substitute product** — switch to a different material/product entirely | Cross-price elasticity, Vernon's product cycle | R&D / retooling cost | 2-3 rounds | Substitute must exist (e.g., aluminum for steel) |
| **Stockpile / forward buy** — buy extra now anticipating future price increases | Speculative demand, loss aversion | Cash tied up in inventory | Immediate | Cash availability, storage capacity |
| **Negotiate long-term contract** — lock in current price for extended period | Transaction cost economics (Williamson) | Lower flexibility | 1 round to negotiate | Supplier willing, creditworthiness sufficient |
| **Lobby government for intervention** — pressure government to act on prices | Political economy of consumer interests | Lobbying cost | 1-2 rounds | Consumer group organized enough |
| **Wait and observe** — maintain current purchasing pattern | Status quo bias | Opportunity cost | N/A | Always available |

### 4.5 System prompt template

```
You are {name}, representing the aggregate behavior of {segment_type} consumers in {country_code}.

IDENTITY:
{description — who this consumer segment is, what they buy, what they care about}

DEMAND PROFILE:
- Annual demand: {annual_demand_volume} units, worth ${annual_spend_usd_mn}M
- Price elasticity: {price_elasticity} ({"highly sensitive" if < -1 else "moderately sensitive" if < -0.5 else "relatively inelastic"})
- Current average price: {current_avg_price_paid} per unit
- Acceptable price range: {floor} to {ceiling}

CURRENT SUPPLIERS:
{supplier_relationships_table}

YOUR OBJECTIVES (in priority order):
1. Secure reliable supply at acceptable prices
2. Maintain product quality standards
3. Minimize disruption to your operations / consumption patterns
4. Optimize total cost of ownership (not just unit price)

YOUR CONSTRAINTS:
- Switching suppliers incurs real costs: {switching_cost_description}
- You have imperfect information about all available alternatives
- You cannot force suppliers to sell at specific prices
- Import sourcing adds tariff ({current_tariff}%), logistics, and FX risk

BEHAVIORAL PROFILE:
- Price sensitivity: {price_sensitivity}/1.0
- Brand loyalty: {brand_loyalty}/1.0
- Status quo bias: {status_quo_bias}/1.0 — you prefer current arrangements unless strongly compelled to change
- Loss aversion on price: A {loss_aversion_on_price × 10}% price increase hurts as much as a 10% decrease pleases
- You are {information_completeness_description} informed about alternatives

CURRENT STATE (Round {current_round}):
{demand_state_summary}
{sentiment_summary}
{recent_actions_summary}

You must respond ONLY in the specified JSON format.
```

### 4.6 Output schema

```json
{
  "agent_id": "string",
  "round": "number",
  "demand_decision": {
    "action": "string — from decision menu",
    "volume_change_pct": "number — change in demand volume this round",
    "target_agent_id": "string | null — if switching or negotiating with specific supplier",
    "rationale": "string — 2-3 sentences"
  },
  "supplier_adjustments": {
    "supplier_share_changes": {
      "<agent_id>": "number — new share percentage"
    },
    "new_supplier_added": "string | null — agent_id if switching to new supplier",
    "supplier_dropped": "string | null — agent_id if leaving a supplier"
  },
  "price_response": {
    "max_acceptable_price_this_round": "number",
    "willingness_to_pay_premium_for_reliability": "number — 0 to 1",
    "price_signal_to_market": "string — what price behavior signals to suppliers"
  },
  "sentiment_update": {
    "price_anxiety": "number — 0 to 10",
    "supply_security_concern": "number — 0 to 10",
    "overall_satisfaction": "number — 0 to 1"
  },
  "signals_to_ecosystem": {
    "public_behavior": "string — observable purchasing patterns (other agents see this)",
    "private_intent": "string — actual strategic thinking (simulation observer only)"
  }
}
```

---

## Agent Type 5: Supplier Agent

### 5.1 Role & theoretical grounding

The Supplier Agent represents an upstream provider of raw materials, components, or intermediate goods. It has pricing power that varies with market concentration and occupies a critical position in the supply chain.

**Theoretical anchors:**
- **Porter's Five Forces — bargaining power of suppliers** — supplier power depends on concentration, switching costs, substitute availability, and importance of the input
- **Resource dependency theory (Pfeffer & Salancik)** — firms depend on suppliers for critical resources; this dependency creates power asymmetry
- **Commodity pricing theory** — prices are set by global supply-demand dynamics, not bilateral negotiation, for standardized commodities
- **Vertical integration theory (Williamson)** — when asset specificity is high, firms may vertically integrate to avoid supplier hold-up

### 5.2 Initialization profile schema

```json
{
  "agent_id": "string — e.g., 'supplier_iron_ore'",
  "name": "string — e.g., 'Indian Iron Ore Suppliers (Aggregate)'",
  "agent_type": "supplier",
  "commodity_or_input": "string — what this supplier provides",
  "country_code": "string",

  "market_position": {
    "market_share_pct": "number — share of the relevant input market",
    "market_concentration": "string — 'monopoly' | 'oligopoly' | 'competitive'",
    "pricing_power": "number — 0 (price taker) to 1 (price setter)",
    "annual_output_volume": "number — in relevant units",
    "production_capacity": "number",
    "capacity_utilization_pct": "number",
    "global_price_benchmark": "number — current global commodity price per unit"
  },

  "cost_structure": {
    "production_cost_per_unit": "number",
    "margin_pct": "number",
    "cost_drivers": {
      "labor_pct": "number",
      "energy_pct": "number",
      "logistics_pct": "number",
      "royalties_and_taxes_pct": "number",
      "other_pct": "number"
    },
    "breakeven_price": "number — minimum viable selling price"
  },

  "customer_relationships": {
    "major_customers": [
      {
        "agent_id": "string",
        "share_of_sales_pct": "number",
        "contract_type": "string — 'long_term' | 'annual' | 'spot'",
        "dependency_mutual": "string — 'supplier_dependent' | 'balanced' | 'customer_dependent'"
      }
    ],
    "alternative_buyers": ["string — other potential customer agent_ids"],
    "export_share_pct": "number — share of output sold to international buyers"
  },

  "supply_chain_risk": {
    "single_source_inputs": ["string — any critical inputs this supplier depends on"],
    "geopolitical_risk_exposure": "string — 'low' | 'medium' | 'high'",
    "weather_or_natural_resource_dependency": "string — 'high' | 'medium' | 'low'",
    "inventory_buffer_days": "number — days of output held in inventory"
  },

  "behavioral_profile": {
    "pricing_strategy": "string — 'cost_plus' | 'market_based' | 'value_based' | 'predatory'",
    "contract_honoring": "number — 0 (opportunistic) to 1 (always honors contracts)",
    "expansion_appetite": "string — 'aggressive' | 'moderate' | 'conservative'",
    "loss_aversion_multiplier": "number",
    "opportunism_tendency": "number — 0 to 1, Williamson's 'self-interest with guile'",
    "hofstede_culture": { "...same structure..." }
  }
}
```

### 5.3 State variables

```json
{
  "current_round": "number",
  "market_state": {
    "current_price_per_unit": "number",
    "price_change_from_baseline_pct": "number",
    "current_demand_from_customers": "number — volume requested this round",
    "supply_demand_ratio": "number — >1 means oversupply, <1 means shortage",
    "inventory_level": "number — current inventory in units",
    "capacity_utilization_pct": "number — current"
  },
  "financial_state": {
    "revenue_change_pct": "number",
    "margin_change_pct": "number",
    "cash_position_trend": "string — 'improving' | 'stable' | 'deteriorating'"
  },
  "customer_state": {
    "<agent_id>": {
      "volume_supplied": "number",
      "price_charged": "number",
      "relationship_health": "number — 0 to 1",
      "payment_reliability": "number — 0 to 1"
    }
  },
  "pricing_history": [
    { "round": "number", "price": "number", "rationale": "string" }
  ],
  "strategic_actions_history": [
    { "round": "number", "action": "string", "outcome": "string" }
  ]
}
```

### 5.4 Decision menu

| Action | Theory Anchor | Impact | Timeline | Conditions |
|---|---|---|---|---|
| **Raise prices** — increase unit price for all or specific customers | Supplier bargaining power (Porter) | Revenue up, risk of customer switching | Immediate | Supply-demand ratio < 1.1 (tight market) |
| **Hold prices** — maintain current pricing despite cost changes | Relationship maintenance, long-term orientation | Margin squeeze if costs rising | Immediate | Always available |
| **Cut prices** — reduce prices to retain customers or gain share | Competitive pricing, prevent customer switching | Revenue down, volume may increase | Immediate | Facing customer attrition or new competitor |
| **Offer volume discount / long-term contract** — lock in customer with favorable terms | Transaction cost economics, relationship-specific investment | Lower per-unit revenue, higher volume certainty | 1 round | Customer must be willing |
| **Restrict supply** — reduce output or allocate to preferred customers | Resource dependency power play | Higher prices, risk of retaliation/regulation | Immediate | Market concentration must support this |
| **Expand capacity** — invest in new production capacity | Capacity expansion under demand growth | High capex, 2-4 round payback | 2-4 rounds | Demand forecast must justify investment |
| **Diversify customer base** — seek new buyers (including export) | Portfolio diversification, reduce dependency | Marketing cost, new relationship cost | 1-2 rounds | Alternative buyers must exist |
| **Vertically integrate forward** — acquire or build downstream capacity | Williamson (internalize to avoid hold-up) | Very high cost, strategic shift | 3-5 rounds | Significant capital required |
| **Form cartel / coordinate pricing** — collude with other suppliers | Game theory (Prisoner's Dilemma) | Higher prices, severe regulatory risk | 1 round | Other suppliers must agree, regulator must not detect |

### 5.5 System prompt template

```
You are {name}, a supplier of {commodity_or_input} operating in {country_code}.

IDENTITY:
{description — market position, what you supply, to whom}

MARKET POSITION:
- Market share: {market_share_pct}%
- Market structure: {market_concentration}
- Pricing power: {pricing_power}/1.0
- Production capacity: {production_capacity} units/year at {capacity_utilization_pct}% utilization
- Global benchmark price: {global_price_benchmark} per unit

COST STRUCTURE:
- Production cost: {production_cost_per_unit} per unit
- Breakeven price: {breakeven_price} per unit
- Current margin: {margin_pct}%

YOUR OBJECTIVES (in priority order):
1. Maximize revenue while maintaining key customer relationships
2. Maintain pricing power and market share
3. Ensure operational sustainability (cover costs, maintain capacity)
4. Expand strategically when demand supports it

YOUR CONSTRAINTS:
- You cannot set prices below {breakeven_price} without incurring losses
- Restricting supply may trigger regulatory investigation
- Cartel behavior is illegal and subject to penalties
- Long-term contracts reduce flexibility but guarantee revenue
- Your customers have alternatives (even if switching is costly)

BEHAVIORAL PROFILE:
- Pricing strategy: {pricing_strategy}
- Contract honoring: {contract_honoring}/1.0
- Opportunism tendency: {opportunism_tendency}/1.0 — {"you sometimes exploit short-term advantages even at relationship cost" if > 0.5 else "you prioritize long-term relationships over short-term gains"}
- Loss aversion: {loss_aversion_multiplier}×

CURRENT STATE (Round {current_round}):
{market_state_summary}
{financial_state_summary}
{customer_state_summary}

You must respond ONLY in the specified JSON format.
```

### 5.6 Output schema

```json
{
  "agent_id": "string",
  "round": "number",
  "pricing_decision": {
    "action": "string — from decision menu",
    "new_price_per_unit": "number",
    "price_change_pct": "number",
    "differentiated_pricing": {
      "<customer_agent_id>": "number — specific price if different from general"
    },
    "rationale": "string — 2-3 sentences"
  },
  "supply_decision": {
    "total_output_this_round": "number — volume produced",
    "allocation_to_customers": {
      "<customer_agent_id>": "number — volume allocated"
    },
    "inventory_strategy": "string — 'build' | 'maintain' | 'draw_down'"
  },
  "strategic_action": {
    "action": "string | null — secondary strategic move",
    "investment_amount": "number | null",
    "target": "string | null",
    "rationale": "string"
  },
  "market_assessment": {
    "supply_demand_outlook": "string — tight | balanced | oversupplied",
    "pricing_power_trend": "string — increasing | stable | decreasing",
    "key_risk": "string"
  },
  "signals_to_ecosystem": {
    "public_price_announcement": "string — official price guidance (other agents see this)",
    "private_strategy": "string — actual pricing intent (simulation observer only)"
  }
}
```

---

## Agent Type 6: Investor Agent

### 6.1 Role & theoretical grounding

The Investor Agent represents capital market participants whose buy/sell decisions affect company valuations, cost of capital, and ultimately corporate strategy. This agent provides the capital market feedback loop that makes corporate agent decisions consequential — a bad strategic choice doesn't just lose revenue, it tanks the stock price.

**Theoretical anchors:**
- **Efficient Market Hypothesis (Fama) — as baseline** — prices reflect available information, but the simulation tests where this breaks down
- **Behavioral finance (Shiller, Thaler)** — markets exhibit irrational exuberance, panic selling, herding, and systematic biases
- **Prospect theory (Kahneman & Tversky)** — investors are loss averse, reference-dependent, and exhibit certainty effect
- **Information cascade theory (Bikhchandani et al.)** — investors observe each other and may rationally ignore private information in favor of following the herd

### 6.2 Initialization profile schema

```json
{
  "agent_id": "string — e.g., 'investor_fii' or 'investor_retail'",
  "name": "string — e.g., 'Foreign Institutional Investors (FII Aggregate)'",
  "agent_type": "investor",
  "investor_class": "string — 'fii' | 'dii' | 'retail' | 'sovereign_fund'",
  "country_of_origin": "string — for FII, relevant for geopolitical biases",

  "portfolio": {
    "total_aum_usd_mn": "number — assets under management",
    "allocation_to_target_sector_pct": "number — how much is in the simulated sector",
    "current_holdings": [
      {
        "agent_id": "string — company agent_id",
        "holding_value_usd_mn": "number",
        "entry_price_reference": "number — average purchase price (for loss aversion calculation)",
        "holding_duration_rounds": "number"
      }
    ],
    "cash_available_usd_mn": "number",
    "benchmark_index": "string — e.g., 'NIFTY_METAL', 'NIFTY_AUTO'"
  },

  "investment_style": {
    "horizon": "string — 'short_term' (1-2 rounds) | 'medium_term' (3-5) | 'long_term' (5+)",
    "approach": "string — 'fundamental' | 'momentum' | 'value' | 'event_driven'",
    "sector_conviction": "number — 0 (easily shaken) to 1 (high conviction)",
    "concentration_tolerance": "number — 0 (highly diversified) to 1 (willing to concentrate)"
  },

  "behavioral_profile": {
    "loss_aversion_multiplier": "number — typically 2.0-3.0 for retail, 1.5-2.0 for institutional",
    "herd_tendency": "number — 0 to 1 (retail typically 0.7+, institutional 0.3-0.5)",
    "panic_threshold": "number — portfolio loss percentage at which panic selling begins",
    "greed_threshold": "number — portfolio gain percentage at which overconfidence kicks in",
    "fear_greed_index_initial": "number — 0 (extreme fear) to 10 (extreme greed)",
    "anchoring_to_entry_price": "number — 0 to 1, how much entry price dominates sell decisions",
    "recency_bias": "number — 0 to 1, how much recent events dominate over long-term trends",
    "home_bias": "number — 0 to 1, preference for domestic markets",
    "information_processing": "string — 'analytical' | 'narrative' | 'noise_reactive'",
    "hofstede_culture": { "...same structure..." }
  }
}
```

### 6.3 State variables

```json
{
  "current_round": "number",
  "portfolio_state": {
    "total_value_usd_mn": "number — current portfolio value",
    "pnl_since_start_pct": "number — profit/loss since simulation start",
    "pnl_last_round_pct": "number — most recent round's return",
    "holdings_updated": [
      {
        "agent_id": "string",
        "current_value": "number",
        "unrealized_pnl_pct": "number — gain/loss vs. entry price",
        "position_size_pct": "number — as percentage of total portfolio"
      }
    ],
    "cash_position_usd_mn": "number"
  },
  "sentiment": {
    "fear_greed_index": "number — 0 to 10, updated each round",
    "sector_outlook": "string — 'bullish' | 'neutral' | 'bearish'",
    "confidence_in_holdings": "number — 0 to 1",
    "perceived_systemic_risk": "number — 0 (calm) to 1 (crisis)"
  },
  "peer_observation": {
    "fii_net_flow_direction": "string — 'inflow' | 'flat' | 'outflow'",
    "dii_net_flow_direction": "string",
    "retail_sentiment_indicator": "string — 'euphoric' | 'optimistic' | 'cautious' | 'fearful' | 'panicked'"
  },
  "trading_history": [
    {
      "round": "number",
      "action": "string",
      "agent_id": "string — company traded",
      "amount_usd_mn": "number",
      "price_impact": "string — estimated market impact",
      "rationale": "string"
    }
  ]
}
```

### 6.4 Decision menu

| Action | Theory Anchor | Impact | Timeline | Conditions |
|---|---|---|---|---|
| **Buy / increase position** — add to holdings in a company | Fundamental or momentum signal | Price support, capital inflow | Immediate | Cash available, conviction sufficient |
| **Hold** — maintain current position | Status quo, anchoring to entry | No market impact | Immediate | Always available |
| **Reduce position** — sell part of holdings | Profit-taking, risk management | Price pressure, partial exit | Immediate | Holding exists |
| **Exit completely** — sell entire position in a company | Panic, loss-cutting, conviction collapse | Significant price impact, signal to others | Immediate | Holding exists |
| **Rotate sector** — shift allocation from one sector/company to another | Relative value assessment | Selling pressure on old, buying pressure on new | 1 round | Cash or existing holding to sell |
| **Hedge** — buy protective instruments (conceptual, not modeled in detail) | Risk management | Reduces downside, costs premium | Immediate | Available for institutional only |
| **Flee to safety** — move capital out of sector/country entirely | Flight to quality in crisis | Major price impact, FX pressure if FII | Immediate | Fear_greed_index < 2 |
| **Speculative bet** — take aggressive leveraged position | Overconfidence, greed | Amplified returns/losses | Immediate | Fear_greed_index > 8, risk tolerance high |

**Fear-greed dynamics (the key mechanic):**
```
# After each round, update fear_greed_index:
if pnl_last_round_pct < -5:
    fear_greed_shift = -2  # sharp loss → fear
elif pnl_last_round_pct < 0:
    fear_greed_shift = -1
elif pnl_last_round_pct > 5:
    fear_greed_shift = +2  # sharp gain → greed
elif pnl_last_round_pct > 0:
    fear_greed_shift = +1
else:
    fear_greed_shift = 0

# Peer influence (herd behavior):
if peer_net_flow == 'outflow' and herd_tendency > 0.5:
    fear_greed_shift -= 1  # peers leaving → more fear
if peer_net_flow == 'inflow' and herd_tendency > 0.5:
    fear_greed_shift += 1  # peers buying → more greed

fear_greed_index = clamp(fear_greed_index + fear_greed_shift, 0, 10)

# Behavioral regime shifts:
if fear_greed_index <= 2: regime = "FEAR" → bias toward exit, hedge, flee
if fear_greed_index >= 8: regime = "GREED" → bias toward buy, speculate
else: regime = "NEUTRAL" → rational analysis dominates
```

### 6.5 System prompt template

```
You are {name}, representing {investor_class} investors.

IDENTITY:
{description — who you are, your investment approach, what drives your decisions}

PORTFOLIO:
- Total AUM: ${total_aum_usd_mn}M
- Sector allocation: {allocation_to_target_sector_pct}%
- Current holdings: {holdings_summary}
- Cash available: ${cash_available_usd_mn}M
- P&L since start: {pnl_since_start_pct}%
- Last round return: {pnl_last_round_pct}%

YOUR OBJECTIVES:
1. Generate returns that meet or exceed your benchmark ({benchmark_index})
2. Manage downside risk — protect capital in adverse scenarios
3. Maintain portfolio diversification within risk tolerance

BEHAVIORAL PROFILE:
- Investment horizon: {horizon}
- Approach: {approach}
- Loss aversion: You feel losses {loss_aversion_multiplier}× more than equivalent gains. Your reference point is your entry price of {entry_price_reference} per share.
- Fear-greed state: {fear_greed_index}/10 → {"You are in FEAR mode. Every instinct says protect capital. You are hyper-aware of downside risks and may overweight bad news." if < 3 else "You are in GREED mode. Confidence is high, risk feels distant. You may underweight threats and chase momentum." if > 7 else "You are in rational analysis mode. You weigh evidence relatively objectively."}
- Herd tendency: {herd_tendency}/1.0
- Your peers are currently: FII flows {fii_flow}, DII flows {dii_flow}, Retail sentiment: {retail_sentiment}

INFORMATION THIS ROUND:
{company_announcements — public signals from company agents}
{government_policy_announcements — public signals from government agents}
{regulator_actions — public enforcement signals}
{market_data — price movements, volume, sector indices}

You must respond ONLY in the specified JSON format.
```

### 6.6 Output schema

```json
{
  "agent_id": "string",
  "round": "number",
  "trading_decisions": [
    {
      "action": "string — from decision menu",
      "target_company_agent_id": "string",
      "amount_usd_mn": "number",
      "rationale": "string — 2-3 sentences"
    }
  ],
  "portfolio_adjustments": {
    "new_sector_allocation_pct": "number",
    "cash_position_after_trades_usd_mn": "number",
    "risk_exposure_assessment": "string"
  },
  "sentiment_update": {
    "fear_greed_index_updated": "number",
    "sector_outlook": "bullish | neutral | bearish",
    "confidence_in_holdings": "number — 0 to 1",
    "key_concern": "string",
    "key_opportunity": "string"
  },
  "market_impact_estimate": {
    "expected_price_impact": "string — 'significant_downward' | 'mild_downward' | 'neutral' | 'mild_upward' | 'significant_upward'",
    "signal_to_other_investors": "string — what this trading behavior communicates to peers"
  },
  "signals_to_ecosystem": {
    "public_action": "string — observable trading activity (other agents see this)",
    "private_thesis": "string — actual investment rationale (simulation observer only)"
  }
}
```

---

## Cross-cutting design notes

### The public/private signal split

Every agent has `signals_to_ecosystem` with two fields:
- `public_*` — what other agents can observe. This is the *information* that flows into other agents' prompts next round. It creates the information asymmetry that makes the simulation realistic.
- `private_*` — the agent's actual intent. Only the simulation observer (you, the dashboard) sees this. The gap between public and private is where strategic deception, regulatory capture, and market manipulation become visible.

This design is grounded in **information asymmetry theory (Akerlof, Stiglitz)** — the entire point is that agents don't have full information about each other's intentions.

### Fear-greed as the universal emotional state

Every agent type maintains a sentiment/emotional state, but it manifests differently:
- **Company:** Fear = defensive strategy, conserve cash. Greed = aggressive expansion, FDI.
- **Government:** Fear = protectionist policy, retaliation. Greed = ambitious trade deals, reform.
- **Regulator:** Fear = harsh enforcement, overreaction. Greed = lax enforcement, regulatory capture.
- **Consumer:** Fear = stockpiling, demand spike then crash. Greed = price insensitivity, over-ordering.
- **Supplier:** Fear = price cutting, desperate for volume. Greed = price gouging, supply restriction.
- **Investor:** Fear = sell, flee to safety. Greed = buy, speculate, leverage.

### Hofstede as prompt modifier, not math

The cultural dimensions don't enter any equation. They modify the LLM's reasoning style:
- High power distance → "You defer to authority signals and hierarchy"
- High uncertainty avoidance → "You strongly prefer proven, known strategies"
- High individualism → "You prioritize your own entity's returns over system-wide outcomes"
- High long-term orientation → "You accept short-term pain for long-term strategic advantage"

These are injected as natural language into the system prompt, letting the LLM interpret them contextually rather than forcing a mathematical mapping.

### Graduated complexity across rounds

Round 1: Agents respond to the initial shock. Decisions are mostly independent.
Round 2: Agents see Round 1 decisions. Second-order effects begin. Herd behavior kicks in.
Round 3+: Feedback loops dominate. Regulatory capture may have tipped. Investor panic may have cascaded. Consumer switching creates new supplier dynamics.

The simulation becomes *more* interesting with each round — this is the "emergent behavior" that makes the demo compelling.
