# Interaction Protocol — Multi-Agent Simulation Engine

> **Purpose:** This document defines how agents interact with each other across simulation rounds. It specifies the simulation loop, information visibility rules, every pairwise interaction channel, and the state resolution logic that the engine computes between rounds. Read this alongside the Agent Architecture Specification.

---

## 1. The simulation loop

Each simulation run follows this structure:

```
INITIALIZE:
  Load shock scenario (JSON)
  Load agent profiles (JSON per agent)
  Build initial world state
  Set round = 0

FOR round = 1 to N:
  PHASE 1 — STATE ASSEMBLY
    For each agent:
      Collect: shock context (round 1 only, persists in memory after)
      Collect: public signals from all visible agents (previous round)
      Collect: agent's own private memory (all rounds)
      Collect: engine-computed state updates (market prices, policy effects)
      Apply: information delay rules (distant agents = 1 round lag)
      Apply: information completeness filter (based on agent's info score)
      Build: agent_prompt = system_prompt + assembled_context

  PHASE 2 — AGENT EXECUTION
    For each agent (can be parallel — no agent sees another's current-round output):
      Call LLM with agent_prompt
      Parse structured JSON response
      Validate against constraint rules
      If invalid: re-prompt with constraint violation message (max 1 retry)
      Store: raw response in agent.memory

  PHASE 3 — STATE RESOLUTION
    Collect all agent responses for this round
    Resolve: market clearing (supply vs demand → price)
    Resolve: policy effects (new tariffs → trade flow changes)
    Resolve: lobbying accumulation → capture score updates
    Resolve: investor actions → valuation changes
    Resolve: fear-greed index updates for all agents
    Resolve: action conflicts (two agents targeting same market)
    Update: world state with all resolved changes

  PHASE 4 — ROUND OUTPUT
    Snapshot the full world state
    Generate round summary (for display/dashboard)
    Check convergence (are agents stabilizing or still shifting?)
    Feed updated state into next round's Phase 1
```

**Critical design decision: simultaneous execution.** All agents in a round decide based on the *previous* round's state. No agent sees another agent's current-round decision. This prevents order-of-execution bias and mirrors real-world information delay — when Tata Steel announces an FDI decision, the Indian government doesn't learn about it until the next "news cycle" (round).

---

## 2. Information visibility rules

This is the most important section for producing realistic emergent behavior. What each agent *cannot* see is as important as what it can.

### 2.1 The visibility matrix

Each cell answers: "What does the ROW agent see about the COLUMN agent?"

| Observer ↓ / Subject → | Company | Government | Regulator | Consumer | Supplier | Investor |
|---|---|---|---|---|---|---|
| **Company** | Public announcement + own private memory if self | Public statement, active policies, tariff rates | Public enforcement actions, investigation status | Public purchasing behavior, demand signals | Public price announcement, supply availability | Public trading activity (buy/sell signals) |
| **Government** | Public announcement, lobbying spend received, financial filings | Own private memory if self, other govts' public statements | Public enforcement actions, recommendations | Aggregate demand data, price indices | Aggregate pricing, import/export volumes | FII/DII flow direction, aggregate sentiment |
| **Regulator** | Public announcement, financial filings, market share data | Public policies, mandate instructions | Own private memory if self | Market price data, complaint signals | Market pricing data, concentration metrics | Trading volume anomalies |
| **Consumer** | Public announcement, product pricing, availability | Public policies, tariff announcements, subsidy availability | Public enforcement outcomes (e.g., anti-dumping duties) | Peer behavior (herd signal) | Public price announcements | N/A (consumers don't track investors) |
| **Supplier** | Purchase orders, contract terms, payment history | Policy announcements, export incentive changes | Public enforcement (is dumping being investigated?) | Demand signals (volume requests) | Competitor pricing (if market-based, not cost-plus) | N/A (suppliers don't track investors) |
| **Investor** | Public announcement, financial projections, analyst estimates | Policy announcements, economic indicators | Enforcement actions (impact on company risk) | Demand trend indicators | Commodity price movements | Peer flows (FII/DII/retail direction) |

### 2.2 What is NEVER visible

- **Private intent** (`private_*` fields from output schema) — only the simulation observer (dashboard) sees these
- **Other agents' behavioral parameters** — Tata Steel doesn't know the government's `capture_vulnerability` score
- **Other agents' fear-greed index** — observable only through *behavior* (aggressive buying → inferred greed)
- **Regulator's capture state** — captured regulators don't announce they're captured; it must be inferred from enforcement patterns
- **Exact financial reserves** of competing companies — public filings show lagged data, not real-time cash position

### 2.3 Information delay rules

```python
def get_information_delay(observer, subject, world_state):
    """
    Returns how many rounds of delay before observer sees subject's actions.
    0 = sees last round's actions this round (normal)
    1 = sees actions from 2 rounds ago (delayed)
    """
    # Same country: no delay
    if observer.country_code == subject.country_code:
        return 0

    # Direct trading relationship: no delay
    if subject.agent_id in observer.direct_partners:
        return 0

    # Same sector but different country: 1 round delay
    if observer.sector == subject.sector:
        return 1

    # Everything else: 1 round delay
    return 1
```

### 2.4 Information noise / completeness

Agents with lower `information_completeness` scores see a degraded version of public signals. This implements bounded rationality at the information level.

```python
def apply_information_filter(agent, signal_list):
    """
    Agents with lower information_completeness see fewer signals.
    Returns a filtered subset of available signals.
    """
    completeness = agent.behavioral_profile.information_completeness  # 0 to 1

    if completeness >= 0.8:
        return signal_list  # sees everything public

    # Randomly drop signals proportional to incompleteness
    keep_probability = completeness
    filtered = [s for s in signal_list if random() < keep_probability]

    # Always keep: direct partner signals, own government's policies
    must_keep = [s for s in signal_list
                 if s.source_agent_id in agent.direct_partners
                 or s.source_agent_id == agent.home_government_id]
    filtered = list(set(filtered + must_keep))

    return filtered
```

---

## 3. Pairwise interaction channels

Every meaningful interaction between agent types is defined here with: what triggers it, what data flows, and what changes in each agent's state.

### 3.1 Company → Government: Lobbying

**Trigger:** Company agent chooses "lobby government" from decision menu.

**Data flow:**
```json
{
  "channel": "lobbying",
  "from_agent_id": "tata_steel",
  "to_agent_id": "gov_india",
  "round": 3,
  "lobbying_spend_usd_mn": 45,
  "requested_policy": "Increase anti-dumping duty on Chinese steel to 25%",
  "argument_framing": "Protecting 50,000 jobs in Jharkhand steel belt",
  "industry_association_backing": true
}
```

**Effect on government agent:**
- `lobbying_pressure_received.total` += lobbying_spend
- `lobbying_pressure_received.top_lobbyists` updated
- `capture_score` recalculated: `total_lobbying / (capture_vulnerability × 100)`
- If `capture_score > 0.7`: government's prompt includes bias toward this lobbyist's preferred policy
- The lobbying *request* appears in government's next-round context as: "You have received lobbying pressure from {company} requesting {policy}. The spend was ${amount}M. Their argument: {framing}."

**Effect on company agent:**
- `cash_reserves` -= lobbying_spend
- `relationships.lobbying_spend_cumulative` += lobbying_spend
- Outcome is NOT known this round — company finds out next round whether the government acted favorably

### 3.2 Government → Company: Policy impact

**Trigger:** Government agent imposes a tariff, grants subsidy, or changes regulation.

**Data flow:**
```json
{
  "channel": "policy_announcement",
  "from_agent_id": "gov_india",
  "to_agent_id": "ALL_DOMESTIC_COMPANIES",
  "round": 2,
  "policy_type": "retaliatory_tariff",
  "target_country": "US",
  "magnitude": "15% tariff on selected US imports",
  "affected_sectors": ["machinery", "agriculture"],
  "effective_round": 3,
  "wto_notified": true
}
```

**Effect on company agents:**
- Companies exporting TO the target country: `export_markets[target].tariff_rate_current` += magnitude
- Companies importing FROM the target country: input costs change proportionally
- All domestic companies: re-evaluate strategic options (new tariff may make FDI more attractive)
- The policy appears in every domestic company's context as a public announcement

**Effect on foreign government agents:**
- `diplomatic_state[announcing_country].trade_war_escalation_level` += 1
- Triggers evaluation of retaliatory response
- The announcement appears as a diplomatic signal in their next-round context

### 3.3 Company → Regulator: Compliance / investigation target

**Trigger:** Engine detects a potential violation, OR another agent files a complaint.

**Violation detection rules (computed by engine):**
```python
def detect_potential_violations(round_state):
    violations = []

    # Market concentration violation
    for sector in round_state.sectors:
        hhi = compute_herfindahl(sector.market_shares)
        if hhi > 2500:  # DOJ threshold for highly concentrated
            violations.append({
                "type": "market_concentration",
                "sector": sector.name,
                "hhi_score": hhi,
                "dominant_firms": sector.top_firms_by_share(3)
            })

    # Dumping detection (selling below cost in export market)
    for company in round_state.companies:
        for market, data in company.export_markets.items():
            if data.export_price < company.production_cost * 0.9:
                violations.append({
                    "type": "potential_dumping",
                    "company": company.agent_id,
                    "market": market,
                    "export_price": data.export_price,
                    "production_cost": company.production_cost
                })

    # Cartel detection (suppliers coordinating prices)
    supplier_prices = [s.current_price for s in round_state.suppliers_in_sector]
    price_variance = variance(supplier_prices)
    if price_variance < threshold and len(supplier_prices) > 2:
        violations.append({
            "type": "potential_cartel",
            "agents": [s.agent_id for s in round_state.suppliers_in_sector],
            "price_variance": price_variance,
            "evidence_strength": 1.0 - (price_variance / normal_variance)
        })

    return violations
```

**Data flow to regulator:**
```json
{
  "channel": "market_signal",
  "round": 4,
  "signals": [
    {
      "type": "dumping_complaint",
      "complainant": "tata_steel",
      "target": "chinese_steel_imports",
      "evidence": "Import price $380/MT vs domestic cost $520/MT",
      "injury_claimed": "12% domestic market share loss in 6 months"
    }
  ]
}
```

**Effect on regulator:**
- Signal added to `market_observations` in next-round context
- Regulator decides whether to initiate investigation (based on evidence strength, capacity, and capture state)
- If captured by the complaining firm: biased toward initiating investigation
- If captured by the accused firm: biased toward ignoring the signal

### 3.4 Regulator → Company: Enforcement action

**Trigger:** Regulator agent chooses an enforcement action from its decision menu.

**Data flow:**
```json
{
  "channel": "enforcement_action",
  "from_agent_id": "reg_dgtr",
  "to_agent_id": "tata_steel",
  "round": 5,
  "action": "provisional_anti_dumping_duty",
  "magnitude": "$200/MT on flat steel imports from China",
  "effective_round": 6,
  "duration_rounds": 4,
  "appeal_window_rounds": 2,
  "legal_basis": "Customs Tariff Act 1975, Section 9A"
}
```

**Effect on targeted company/imports:**
- Import-competing domestic companies: competitive relief → revenue improvement
- Importing companies/consumers: cost increase = duty amount
- The enforcement action is PUBLIC — all agents see it in next-round context
- Affects trade flow calculations in engine's state resolution

**Effect on regulator:**
- `enforcement_actions_history` updated
- `market_credibility_score` adjusts based on whether the action is seen as proportional
- If the action is later overturned on appeal: credibility drops

### 3.5 Company ↔ Consumer: Supply-demand interaction

**Trigger:** Automatic every round — the engine mediates supply and demand.

**Company → Consumer (supply side):**
```json
{
  "channel": "market_offering",
  "from_agent_id": "tata_steel",
  "round": 3,
  "product": "flat_steel",
  "price_per_unit": 52000,
  "available_volume_mt": 800000,
  "delivery_timeline": "immediate",
  "quality_grade": "IS_2062_E250",
  "public_announcement": "Tata Steel maintains stable pricing despite import cost pressures"
}
```

**Consumer → Company (demand side):**
```json
{
  "channel": "purchase_decision",
  "from_agent_id": "consumer_industrial_steel",
  "round": 3,
  "supplier_preferences": {
    "tata_steel": { "volume_requested_mt": 300000, "max_price_acceptable": 54000 },
    "jsw_steel": { "volume_requested_mt": 200000, "max_price_acceptable": 53000 },
    "imports_china": { "volume_requested_mt": 100000, "max_price_acceptable": 48000 }
  },
  "total_demand_mt": 600000,
  "willingness_to_pay_premium": 0.3,
  "public_behavior": "Industrial buyers maintaining steady procurement, no panic buying"
}
```

**Engine resolves this into a market clearing:**
```python
def resolve_market(supply_offers, demand_requests, round_state):
    """
    Simple market clearing: match supply and demand, determine realized price.
    Not a full order book — simplified for simulation purposes.
    """
    total_supply = sum(offer.available_volume for offer in supply_offers)
    total_demand = sum(request.total_demand for request in demand_requests)

    supply_demand_ratio = total_supply / total_demand if total_demand > 0 else float('inf')

    # Price discovery: weighted average of offered prices adjusted by S/D ratio
    avg_offered_price = weighted_avg(supply_offers, key='price', weight='volume')

    if supply_demand_ratio < 0.9:  # shortage
        realized_price = avg_offered_price * 1.1  # 10% premium
        unmet_demand_pct = (1 - supply_demand_ratio) * 100
    elif supply_demand_ratio > 1.1:  # oversupply
        realized_price = avg_offered_price * 0.95  # 5% discount pressure
        unmet_demand_pct = 0
    else:  # balanced
        realized_price = avg_offered_price
        unmet_demand_pct = 0

    # Apply tariff effects if imports are in the mix
    for offer in supply_offers:
        if offer.is_import:
            offer.effective_price = offer.price * (1 + round_state.tariff_rate / 100)

    # Allocate volume: cheapest effective price first, up to demand limits
    allocation = allocate_by_price_preference(supply_offers, demand_requests)

    return MarketClearing(
        realized_price=realized_price,
        supply_demand_ratio=supply_demand_ratio,
        unmet_demand_pct=unmet_demand_pct,
        allocation=allocation
    )
```

### 3.6 Company ↔ Supplier: Procurement interaction

**Trigger:** Automatic every round — supplier prices and company demand interact.

**Supplier → Company (pricing signal):**
```json
{
  "channel": "supplier_pricing",
  "from_agent_id": "supplier_iron_ore",
  "round": 3,
  "commodity": "iron_ore_62pct",
  "price_per_unit": 6800,
  "price_change_pct": 5.2,
  "available_volume": 15000000,
  "contract_terms_offered": "Annual contract at 6500/MT for 12MT+ commitment",
  "public_announcement": "Iron ore prices firm on strong domestic steel demand"
}
```

**Company → Supplier (procurement decision — embedded in company output):**
```json
{
  "channel": "procurement_intent",
  "from_agent_id": "tata_steel",
  "round": 3,
  "supplier_agent_id": "supplier_iron_ore",
  "volume_requested": 12000000,
  "max_acceptable_price": 7000,
  "contract_preference": "long_term",
  "alternative_sourcing_signal": "Exploring Australian ore imports if domestic prices exceed 7200"
}
```

**Effect on supplier state:**
- Customer demand data updated
- If company signals alternative sourcing: supplier's `pricing_power_trend` shifts toward "decreasing"
- If company accepts long-term contract: supplier's revenue certainty improves, flexibility decreases

**Effect on company state:**
- Raw material cost updated in cost_structure
- If prices rise significantly: margin compression flows through to financial_health
- Company may cite input cost pressure as rationale for raising own product prices (cost pass-through)

### 3.7 Investor ↔ Company: Capital market feedback loop

**Trigger:** Investor agent makes trading decisions based on company actions and market signals.

**Company → Investor (information signal):**
The investor sees the company's `public_announcement` from each round — this is the *only* signal the company sends. The investor also sees:
- Financial projections from the company's output
- Government policy announcements that affect the company
- Regulator enforcement actions targeting the company
- Market clearing price and volume data

**Investor → Company (market consequence):**
```json
{
  "channel": "market_valuation_impact",
  "from_agent_id": "investor_fii",
  "round": 3,
  "target_company_id": "tata_steel",
  "action": "reduce_position",
  "amount_usd_mn": 120,
  "estimated_price_impact": "mild_downward",
  "public_action": "FII selling observed in metal sector"
}
```

**Engine computes valuation change:**
```python
def compute_valuation_impact(investor_actions, company):
    """
    Aggregate all investor buy/sell actions for a company
    and compute the net valuation impact.
    """
    net_flow = 0
    for action in investor_actions:
        if action.target == company.agent_id:
            if action.action in ['buy', 'increase_position', 'speculative_bet']:
                net_flow += action.amount_usd_mn
            elif action.action in ['reduce_position', 'exit_completely', 'flee_to_safety']:
                net_flow -= action.amount_usd_mn

    # Compute price impact based on net flow vs market cap
    market_cap_estimate = company.financials.revenue_usd_mn * 3  # rough P/S multiple
    flow_as_pct_of_mcap = (net_flow / market_cap_estimate) * 100

    if flow_as_pct_of_mcap < -5:
        impact = "significant_downward"
        valuation_change_pct = flow_as_pct_of_mcap * 1.5  # amplified by sentiment
    elif flow_as_pct_of_mcap < -1:
        impact = "mild_downward"
        valuation_change_pct = flow_as_pct_of_mcap
    elif flow_as_pct_of_mcap > 5:
        impact = "significant_upward"
        valuation_change_pct = flow_as_pct_of_mcap * 1.3
    elif flow_as_pct_of_mcap > 1:
        impact = "mild_upward"
        valuation_change_pct = flow_as_pct_of_mcap
    else:
        impact = "neutral"
        valuation_change_pct = 0

    return ValuationImpact(
        impact=impact,
        valuation_change_pct=valuation_change_pct,
        net_flow_usd_mn=net_flow
    )
```

**Effect on company agent:**
- Valuation change appears in next-round context: "Your market valuation changed by {X}% this round due to investor activity."
- Severe valuation drops affect `fear_greed_index` (downward) and may trigger defensive strategies
- Cost of capital implicitly increases when valuation drops (harder to raise funds for FDI)

**Effect on other investors:**
- Aggregate flows visible as `peer_observation.fii_net_flow_direction`
- Triggers herd behavior: if most peers are selling, high-herd-tendency investors feel pressure to sell too
- This is the **information cascade mechanism** — sell pressure begets more sell pressure

### 3.8 Government ↔ Government: Diplomatic interaction

**Trigger:** One government's policy action affects another country.

**Data flow:**
```json
{
  "channel": "diplomatic_signal",
  "from_agent_id": "gov_india",
  "to_agent_id": "gov_us",
  "round": 3,
  "signal_type": "escalation",
  "context": "India imposed 15% retaliatory tariff on US agricultural imports",
  "public_statement": "India reserves the right to protect its strategic interests while remaining open to bilateral negotiation",
  "private_stance": "Willing to reduce to 8% if US exempts pharma and IT services from its tariff",
  "diplomatic_tone": "firm_but_open"
}
```

**Engine resolves bilateral relationship:**
```python
def update_diplomatic_state(gov_a, gov_b, round_actions):
    """
    Update the bilateral relationship score based on this round's actions.
    """
    relationship = gov_a.diplomatic_state[gov_b.country_code]

    # Escalation actions worsen relationship
    if gov_a.action.type in ['retaliatory_tariff', 'safeguard_duty']:
        relationship.score -= 0.2
        relationship.trade_war_escalation += 1

    # Negotiation offers improve relationship
    if gov_a.action.type in ['negotiate_bilateral', 'offer_concession']:
        relationship.score += 0.1
        relationship.active_negotiations = True

    # Patience is neutral but prevents escalation
    if gov_a.action.type == 'strategic_patience':
        relationship.trade_war_escalation = max(0, relationship.trade_war_escalation - 0.5)

    # Clamp values
    relationship.score = clamp(relationship.score, -1.0, 1.0)
    relationship.trade_war_escalation = clamp(relationship.trade_war_escalation, 0, 5)

    return relationship
```

### 3.9 Company ↔ Company: Competitive dynamics

**Trigger:** Multiple companies operate in the same market/sector.

Companies do NOT communicate directly. They observe each other through public signals only. The competitive interaction is mediated by the engine:

```python
def compute_competitive_effects(companies_in_sector, market_clearing):
    """
    When one company acts, it affects others in the same sector.
    """
    effects = {}

    for company in companies_in_sector:
        effects[company.agent_id] = {}

        # If a competitor chose price war: all firms face margin pressure
        for competitor in companies_in_sector:
            if competitor.agent_id == company.agent_id:
                continue

            if competitor.primary_action.action == 'price_war':
                effects[company.agent_id]['margin_pressure'] = -2.0  # percentage points
                effects[company.agent_id]['competitive_signal'] = (
                    f"{competitor.name} initiated aggressive pricing in your market"
                )

            # If a competitor diverted exports to same target market
            if (competitor.primary_action.action == 'export_diversion'
                and competitor.primary_action.target_market == company.primary_export_market):
                effects[company.agent_id]['market_share_pressure'] = -1.5
                effects[company.agent_id]['competitive_signal'] = (
                    f"{competitor.name} is diverting exports to {company.primary_export_market}, "
                    f"increasing competition"
                )

            # If a competitor invested in FDI in same country: future competitive threat
            if (competitor.primary_action.action == 'fdi'
                and competitor.primary_action.target_market in company.export_markets):
                effects[company.agent_id]['future_threat'] = (
                    f"{competitor.name} is building capacity in "
                    f"{competitor.primary_action.target_market} — "
                    f"local production will undercut your exports within 2-3 rounds"
                )

    return effects
```

**What companies see about each other (next round):**
- Public announcements only (e.g., "JSW Steel announced a new export hub in Vietnam")
- Market share changes (computed by engine, published as market data)
- Pricing behavior (if operating in same market, price is visible through market clearing)
- They do NOT see each other's strategic rationale, cash reserves, or private intent

### 3.10 Supplier ↔ Supplier: Cartel / coordination dynamics

**Trigger:** Multiple suppliers in same commodity market, especially oligopoly.

**If a supplier chooses "form cartel / coordinate pricing":**
```json
{
  "channel": "cartel_attempt",
  "from_agent_id": "supplier_iron_ore_a",
  "round": 4,
  "proposed_to": ["supplier_iron_ore_b", "supplier_iron_ore_c"],
  "proposed_price_floor": 7500,
  "proposed_volume_restriction": "Each member caps output at 80% capacity",
  "expected_benefit": "15% price increase within 2 rounds"
}
```

**Engine resolves cartel dynamics using Prisoner's Dilemma logic:**
```python
def resolve_cartel_attempt(proposer, invited_suppliers, regulator, round_state):
    """
    Each invited supplier independently decides: cooperate or defect.
    Classic Prisoner's Dilemma — mutual cooperation is unstable.
    """
    decisions = {}
    for supplier in invited_suppliers:
        # Supplier's LLM decides based on:
        # - Short-term gain from defection (undercut cartel price, steal volume)
        # - Long-term gain from cooperation (higher prices for all)
        # - Risk of regulatory detection
        # The supplier's opportunism_tendency and contract_honoring parameters shape this
        decisions[supplier.agent_id] = supplier.decide_cartel_response(proposer, round_state)

    all_cooperate = all(d == 'cooperate' for d in decisions.values())

    if all_cooperate:
        # Cartel forms: prices rise, but detection risk begins
        detection_probability = compute_detection_probability(
            num_members=len(decisions) + 1,
            regulator_competence=regulator.capacity.technical_competence,
            price_variance_change=compute_price_variance_change(round_state),
            regulator_captured=regulator.integrity_state.is_captured
        )
        return CartelOutcome(
            formed=True,
            price_effect=+15,  # percent
            detection_probability=detection_probability,
            visible_signal="Commodity prices rose sharply on tightening supply"
        )
    else:
        # Defection: cartel fails, defector gains short-term volume
        defectors = [k for k, v in decisions.items() if v == 'defect']
        return CartelOutcome(
            formed=False,
            defectors=defectors,
            price_effect=-5,  # price war erupts
            visible_signal="Commodity market sees price instability as suppliers compete"
        )
```

### 3.11 Government → Regulator: Mandate & independence

**Trigger:** Government sets or changes regulatory mandate, OR exerts political pressure.

```json
{
  "channel": "regulatory_mandate",
  "from_agent_id": "gov_india",
  "to_agent_id": "reg_dgtr",
  "round": 2,
  "mandate_update": "Prioritize anti-dumping investigations on Chinese steel imports",
  "political_pressure_level": "moderate",
  "budget_change": "+5% for current fiscal year",
  "independence_signal": "Government expects swift action on steel dumping complaints"
}
```

**Effect on regulator:**
- If `political_independence > 0.7`: regulator notes the pressure but decides independently
- If `political_independence < 0.4`: regulator's prompt includes: "The government has signaled urgency on {sector} investigations. You feel pressure to align with this direction."
- Budget changes affect `investigation_throughput` (more budget = can handle more cases)
- This is a *soft* influence channel — the regulator's LLM decides how much to defer based on its independence score

### 3.12 Investor → Investor: Herd dynamics

**Trigger:** Automatic every round — investors observe each other's aggregate behavior.

No direct investor-to-investor communication. Instead, the engine computes aggregate flow data that all investors see:

```python
def compute_investor_herd_signals(all_investor_actions, round_state):
    """
    Aggregate investor behavior into signals that other investors observe.
    This is what creates information cascades.
    """
    fii_net = sum(
        a.amount * (1 if a.action in ['buy'] else -1)
        for a in all_investor_actions
        if a.investor_class == 'fii' and a.action in ['buy', 'reduce_position', 'exit_completely']
    )
    dii_net = sum(
        a.amount * (1 if a.action in ['buy'] else -1)
        for a in all_investor_actions
        if a.investor_class == 'dii' and a.action in ['buy', 'reduce_position', 'exit_completely']
    )

    return HerdSignals(
        fii_flow='inflow' if fii_net > 0 else 'outflow' if fii_net < 0 else 'flat',
        dii_flow='inflow' if dii_net > 0 else 'outflow' if dii_net < 0 else 'flat',
        retail_sentiment=infer_retail_sentiment(all_investor_actions),
        aggregate_sector_flow_usd_mn=fii_net + dii_net,
        momentum_signal='positive' if (fii_net + dii_net) > 0 else 'negative'
    )
```

These signals feed into every investor's next-round prompt, creating the feedback loop where selling begets selling and buying begets buying.

---

## 4. State resolution engine

After all agents act in a round, the engine computes consequences. These are deterministic calculations, not LLM calls.

### 4.1 Trade flow recalculation

When tariffs change, trade routes adjust:

```python
def recalculate_trade_flows(world_state):
    """
    When a tariff changes on one route, trade diverts to alternatives.
    This is the core shock propagation mechanism.
    """
    for trade_route in world_state.all_trade_routes:
        # Effective cost = base_price + tariff + transaction_costs + logistics
        trade_route.effective_cost = (
            trade_route.base_price
            * (1 + trade_route.tariff_rate / 100)
            * trade_route.institutional_friction  # North's transaction costs
            + trade_route.logistics_cost
        )

    # For each product/commodity, rank routes by effective cost
    for product in world_state.products:
        routes = world_state.get_routes_for_product(product)
        routes.sort(key=lambda r: r.effective_cost)

        # Demand shifts toward cheapest effective route
        # But switching is not instant — only shift a fraction per round
        max_shift_per_round = 0.2  # 20% of volume can shift per round
        for route in routes:
            route.volume = redistribute_volume(
                routes, max_shift_per_round, product.total_demand
            )

    return world_state
```

### 4.2 Lobbying → Capture score update

```python
def update_capture_scores(world_state):
    """
    Accumulate lobbying pressure and update capture status for all regulators
    and government agents.
    """
    for agent in world_state.capturable_agents:  # regulators + governments
        total_lobbying = sum(
            action.lobbying_spend
            for action in world_state.round_actions
            if action.action == 'lobby_government' and action.target == agent.agent_id
        )

        agent.integrity_state.cumulative_lobbying += total_lobbying

        # Compute capture score
        threshold = agent.integrity_profile.capture_threshold
        vulnerability = agent.behavioral_profile.capture_vulnerability
        effective_threshold = threshold / vulnerability  # lower vulnerability = harder to capture

        agent.integrity_state.capture_score = min(1.0,
            agent.integrity_state.cumulative_lobbying / effective_threshold
        )

        # Determine capture state
        was_captured = agent.integrity_state.is_captured
        agent.integrity_state.is_captured = agent.integrity_state.capture_score > 0.7

        # Track who captured the agent
        if agent.integrity_state.is_captured:
            top_lobbyists = sorted(
                agent.integrity_state.lobbying_by_source.items(),
                key=lambda x: x[1], reverse=True
            )
            agent.integrity_state.captured_by = [l[0] for l in top_lobbyists[:3]]

        # Log state change for dashboard
        if agent.integrity_state.is_captured and not was_captured:
            world_state.events.append({
                "type": "CAPTURE_TIPPING_POINT",
                "round": world_state.current_round,
                "agent": agent.agent_id,
                "captured_by": agent.integrity_state.captured_by,
                "narrative": f"{agent.name} integrity breached — regulatory independence compromised"
            })
```

### 4.3 Fear-greed index update

Applied universally across all agent types after each round:

```python
def update_fear_greed(agent, round_outcome):
    """
    Universal sentiment update. The shift direction is the same logic,
    but what constitutes a 'loss' differs by agent type.
    """
    # Determine the agent's "performance" this round
    if agent.agent_type == 'company':
        performance = round_outcome.revenue_change_pct
    elif agent.agent_type == 'investor':
        performance = round_outcome.portfolio_pnl_pct
    elif agent.agent_type == 'government':
        performance = round_outcome.approval_rating_change
    elif agent.agent_type == 'consumer':
        performance = -round_outcome.price_change_pct  # price up = bad for consumer
    elif agent.agent_type == 'supplier':
        performance = round_outcome.margin_change_pct
    elif agent.agent_type == 'regulator':
        performance = round_outcome.credibility_change

    # Base shift from performance
    if performance < -5:
        shift = -2
    elif performance < 0:
        shift = -1
    elif performance > 5:
        shift = +2
    elif performance > 0:
        shift = +1
    else:
        shift = 0

    # Peer influence (herd behavior)
    peer_sentiment = get_peer_average_sentiment(agent, round_outcome.world_state)
    herd_pull = (peer_sentiment - agent.sentiment.fear_greed_index) * agent.behavioral_profile.herd_tendency
    shift += round(herd_pull * 0.5)  # dampen the herd pull to avoid oscillation

    # Loss aversion asymmetry: losses shift fear faster than gains shift greed
    if shift < 0:
        shift = int(shift * agent.behavioral_profile.loss_aversion_multiplier)

    # Apply and clamp
    agent.sentiment.fear_greed_index = clamp(
        agent.sentiment.fear_greed_index + shift, 0, 10
    )
```

### 4.4 Action conflict resolution

When multiple agents take contradictory actions in the same round:

```python
def resolve_conflicts(round_actions, world_state):
    """
    Handle cases where agent actions conflict.
    """
    # CONFLICT: Two companies divert exports to the same small market
    # Resolution: Market absorbs less than both wanted — prices drop
    export_diversion_targets = {}
    for action in round_actions:
        if action.action == 'export_diversion':
            target = action.target_market
            export_diversion_targets.setdefault(target, []).append(action)

    for target, actions in export_diversion_targets.items():
        if len(actions) > 1:
            market_capacity = world_state.market_capacity[target]
            total_diverted = sum(a.volume for a in actions)
            if total_diverted > market_capacity * 1.2:
                # Oversupply in target market: prices drop, volume rationed
                for action in actions:
                    action.realized_volume = action.volume * (market_capacity / total_diverted)
                    action.price_penalty_pct = -10  # oversupply drives prices down
                world_state.events.append({
                    "type": "MARKET_FLOOD",
                    "round": world_state.current_round,
                    "market": target,
                    "competing_agents": [a.agent_id for a in actions],
                    "narrative": f"Multiple exporters flooding {target} — prices collapse"
                })

    # CONFLICT: Government imposes tariff while negotiating with same country
    # Resolution: Negotiation fails, diplomatic score drops further
    for gov in world_state.governments:
        if (gov.primary_action.type == 'retaliatory_tariff'
            and gov.secondary_action.type == 'negotiate_bilateral'
            and gov.primary_action.target == gov.secondary_action.target):
            # Can't retaliate and negotiate simultaneously — retaliation wins
            gov.secondary_action.status = 'abandoned'
            gov.secondary_action.failure_reason = 'contradicted by simultaneous tariff action'

    # CONFLICT: Investor buys while company simultaneously announces bad news
    # Resolution: No conflict — investor acted on pre-announcement information
    # This is realistic: investors trade on stale info in the same "round"
    # The bad news hits their portfolio next round via valuation impact
```

---

## 5. Prompt assembly — what each agent actually receives

Here is the exact structure of what gets assembled into each agent's LLM prompt each round. This is the **input** each agent receives.

### 5.1 Common prompt structure (all agents)

```
[SYSTEM PROMPT — from Agent Architecture Specification, static per agent]

--- ROUND {N} CONTEXT ---

EXTERNAL SHOCK (if round 1, or if new shock injected):
{shock.name}: {shock.description}
Category: {shock.category} | Severity: {shock.severity}
Affected sectors: {shock.affected_sectors}
Context: {shock.context}

WHAT HAPPENED LAST ROUND:
{For each visible agent's PUBLIC signal from round N-1:}
- {agent.name} ({agent.type}): {agent.signals.public_*}
{End for}

MARKET DATA THIS ROUND:
- Realized market price: {market_clearing.realized_price} per unit
- Supply/demand ratio: {market_clearing.supply_demand_ratio}
- Your sector's trade flow changes: {trade_flow_summary}
- FX rate changes: {fx_impact if relevant}

COMPETITIVE INTELLIGENCE:
{competitive_effects computed by engine — market share shifts, competitor actions}

ENGINE-COMPUTED IMPACTS ON YOU:
- Revenue impact from tariff changes: {calculated_revenue_change}
- Cost impact from input price changes: {calculated_cost_change}
- Valuation change from investor activity: {valuation_impact}
- Regulatory actions affecting you: {enforcement_summary}

YOUR UPDATED STATE:
{agent.state — full private state including memory of all past rounds}

ACTIONS AVAILABLE THIS ROUND:
{filtered_decision_menu — only valid actions based on current constraints}

Respond in the specified JSON format.
```

### 5.2 Agent-specific context additions

**Company agents additionally receive:**
- Peer behavior summary: "{X} of {Y} sector peers chose defensive strategies last round"
- Lobbying outcome (if lobbied last round): "The government {did/did not} act on your lobbying request"
- Contract status: active JVs, FDI commitments, their progress

**Government agents additionally receive:**
- Lobbying pressure summary: "You received ${X}M in lobbying from: {list}"
- Diplomatic inbox: "Country {X} has signaled {escalation/deescalation/negotiation}"
- WTO compliance check: "Your proposed action {would/would not} comply with WTO obligations"
- Election proximity reminder: "Your next election is {N} years away. Public approval: {X}%"

**Regulator agents additionally receive:**
- Market anomaly signals: engine-detected potential violations
- Complaint inbox: formal complaints from other agents
- Capacity check: "You are currently running {N} of {max} simultaneous investigations"
- Capture state injection (if captured): the modified behavioral prompt

**Consumer agents additionally receive:**
- Price comparison: current domestic vs import prices across suppliers
- Substitute availability: alternative products/materials and their prices
- Peer purchasing behavior: "Most buyers in your segment are {stockpiling/reducing/switching}"

**Supplier agents additionally receive:**
- Customer demand aggregation: total volume requested by all customers
- Competitor pricing: other suppliers' announced prices (if market-based, not opaque)
- Inventory status: current stock levels and production utilization

**Investor agents additionally receive:**
- Full public signal compilation from all agent types (they have the broadest information access)
- Technical indicators: price momentum, volume trends, sector fund flows
- Peer flow data: FII/DII/retail aggregate buying and selling patterns

---

## 6. Output summary — what each agent produces

Every agent produces one structured JSON response per round (defined in Agent Architecture Spec). The engine extracts:

| Extracted Field | Used By Engine For |
|---|---|
| `primary_action` + `secondary_action` | State resolution, conflict detection, trade flow changes |
| `signals_to_ecosystem.public_*` | Next round's context for visible agents |
| `signals_to_ecosystem.private_*` | Dashboard display only — never shared with other agents |
| `assessment.fear_greed_index_updated` | Validated against engine's own calculation — if mismatch, engine value wins |
| `financial_projections` | Cross-checked with engine calculations — agent projections may be wrong (bounded rationality) |

**Critical rule: Agent projections can be wrong.** The agent's `financial_projections` field represents what the agent *expects* to happen. The engine's state resolution computes what *actually* happens. The gap between expectation and reality is what drives agent surprise, adaptation, and learning across rounds. If a company projects +5% revenue but the engine computes -3% (because a competitor flooded their target market), that surprise shifts fear-greed toward fear and may trigger a strategy change next round.

---

## 7. Convergence detection

The simulation should run enough rounds for emergent dynamics to play out but stop when agents stabilize:

```python
def check_convergence(round_history, min_rounds=3, max_rounds=8):
    """
    Detect whether the simulation has converged (agents have settled into stable strategies)
    or is still producing meaningful change.
    """
    if len(round_history) < min_rounds:
        return False  # always run at least min_rounds

    if len(round_history) >= max_rounds:
        return True  # hard cap to limit API costs

    # Check if agent strategies are stabilizing
    last_3_rounds = round_history[-3:]
    strategy_changes = 0
    total_agents = 0

    for agent_id in last_3_rounds[0].agent_ids:
        total_agents += 1
        actions = [r.get_agent_action(agent_id) for r in last_3_rounds]
        if len(set(a.primary_action.action for a in actions)) > 1:
            strategy_changes += 1

    change_rate = strategy_changes / total_agents

    # Check if market prices are stabilizing
    prices = [r.market_clearing.realized_price for r in last_3_rounds]
    price_volatility = max(prices) - min(prices)
    price_stable = price_volatility < (prices[0] * 0.05)  # within 5% band

    # Converged if fewer than 20% of agents changed strategy AND prices stable
    return change_rate < 0.2 and price_stable
```

---

## 8. Complete round example — tariff shock, round 2

To make the interaction concrete, here is a narrative walkthrough of round 2 after a US tariff shock:

**Round 1 recap:** US imposed 50% tariff on Indian steel. All agents reacted independently to the initial shock. Tata Steel chose export diversion to ASEAN. Government of India chose retaliatory tariff on US agriculture. DGTR initiated anti-dumping investigation on Chinese steel. Consumer began stockpiling. Supplier held prices. FII investors reduced positions.

**Round 2 — Phase 1 (state assembly):**

Tata Steel's prompt now includes:
- "Government of India announced 15% retaliatory tariff on US agricultural imports"
- "DGTR initiated anti-dumping investigation on Chinese flat steel"
- "FII investors were net sellers in the metal sector last round"
- "Your market valuation dropped 4.2% due to investor selling"
- "Your export diversion to ASEAN is in progress (1 of 2 rounds)"
- "JSW Steel also announced export diversion to ASEAN" ← competitive intelligence!
- Peer summary: "2 of 4 steel companies chose defensive strategies last round"

Government of India's prompt now includes:
- "Tata Steel spent $45M lobbying for higher anti-dumping duties on Chinese steel"
- "FICCI spent $30M lobbying for bilateral negotiation with US"
- "Your capture score is now 0.35/1.0"
- "US-India diplomatic relationship: -0.4 (deteriorating), escalation level: 2/5"
- "ASEAN trade routes seeing increased volume from Indian exporters"
- "Public approval for trade policy: 62% (protectionist sentiment rising)"

**Round 2 — Phase 2 (agent execution):**

All agents receive their assembled prompts and respond simultaneously. Let's say:
- Tata Steel continues ASEAN diversion but adds secondary action: lobby for PLI subsidy
- Government of India chooses bilateral negotiation with US (FICCI lobbying + rational analysis)
- DGTR imposes provisional anti-dumping duty on Chinese steel ($200/MT)
- Consumer switches some procurement to domestic (dumping duty makes imports expensive)
- Supplier raises prices 3% (domestic demand rising as imports become costlier)
- FII investors hold positions (government's negotiation signal reduces panic)

**Round 2 — Phase 3 (state resolution):**

The engine computes:
- Trade flows: ASEAN route absorbing Indian steel diverted from US, but both Tata and JSW targeting the same market → oversupply risk
- Anti-dumping duty: Chinese steel effective price rises $200/MT → domestic producers benefit
- Market clearing: domestic steel price rises 4% (imports more expensive, demand constant)
- Lobbying accumulation: Tata Steel's cumulative lobbying of government now at $90M → capture score rising
- Investor sentiment: FII flow direction flips from "outflow" to "flat" → positive signal
- Diplomatic state: India-US escalation holds at level 2 (negotiation offer prevents further escalation)

**Round 2 — Phase 4 (output):**

The engine snapshots the full state. Key events flagged for dashboard:
- "MARKET_FLOOD risk: Multiple Indian exporters targeting ASEAN steel market"
- "PRICE_IMPACT: Domestic steel price +4% on anti-dumping duty"
- "DIPLOMATIC: India-US escalation paused — bilateral negotiation initiated"
- "CAPTURE_WATCH: Government capture score rising (0.35 → 0.42)"

This state feeds into Round 3, where the ASEAN market flood becomes visible to all agents, potentially triggering ASEAN governments to consider their own protective measures — a second-order effect that no individual agent planned.
