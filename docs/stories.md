# Implementation Stories — Multi-Agent Economic Simulation

> **Purpose:** This is the complete implementation plan. Every story here, when implemented, produces a fully working, demo-ready MBA simulation application. Stories are ordered by dependency. A developer should implement each story in sequence and have a running system by the end.

---

## Meta: Assumptions and Conventions

- **Environment:** Python 3.11+, `uv` for dependency management
- **LLM backend:** OpenAI SDK → OpenRouter (`https://openrouter.ai/api/v1`) via `OPENROUTER_API_KEY`
- **Models:** `moonshotai/kimi-k2` (dev/fast), `claude-sonnet-4-6` (production)
- **Pydantic:** v2 syntax (`model_validator`, `field_validator`, not v1 `@validator`)
- **Async:** `asyncio` for parallel LLM calls; `nest_asyncio` for Jupyter compatibility
- **Tests:** `pytest` with zero LLM calls — all LLM interactions are mocked or replayed from fixtures
- **Primary demo artifact:** Jupyter notebook (`notebooks/01_tariff_shock_demo.ipynb`)

---

## Dependency Map

```
Story 1 (scaffold) → Stories 2–5 (models)
Stories 2–5 (models) → Stories 6–8 (JSON data files)
Stories 2–3 (models) → Story 9 (parser)
Story 4 (world state) → Story 10 (visibility)
Stories 4, 10 → Story 11 (prompt builder)
Stories 9, 11 → Story 12 (base agent)
Story 4 → Stories 13, 14, 15, 16 (sub-engines)
Stories 13, 14, 15, 16 → Story 17 (resolver)
Stories 12, 17 → Story 18 (simulation engine)
Story 18 → Stories 19, 21 (results + notebook)
Stories 9, 10, 13, 17 → Story 20 (unit tests)
Story 18 → Story 22 (smoke + integration tests)
Story 19 → Story 23 (dashboard — P2)
```

---

## Priority Legend

| Priority | Meaning                                                            |
| -------- | ------------------------------------------------------------------ |
| **P0**   | Must-have for a working demo. Block everything else until done.    |
| **P1**   | Important for realistic behavior but demo can run without it.      |
| **P2**   | Nice-to-have; implement only if time permits after P0+P1 complete. |

---

## Week-by-Week Plan

**Week 1 (Days 1–5):** Stories 1–8 — scaffolding, models, data files. Zero LLM calls. Fast iteration.  
**Week 1–2 (Days 5–10):** Stories 9–15, 17–18 — parser, agents, sub-engines, resolver, engine. Critical path.  
**Week 2 (Days 10–14):** Stories 16, 19–22 — sentiment, output, tests, notebook.  
**Week 3/buffer:** Story 14 (capture polish), Story 23 (dashboard), presentation prep.

**Single most important milestone:** Story 18 running end-to-end with 2 agents and 1 round — even if market clearing is a stub.

---

## Story 1: Project Scaffolding and Dependency Manifest

**Epic:** Infrastructure  
**Priority:** P0  
**Depends on:** nothing

### What to build

Create the complete directory skeleton, `requirements.txt`, and all `__init__.py` files so every module is importable from the start. This is the foundation everything else builds on.

### Acceptance criteria

- [ ] All directories exist: `agents/`, `agents/profiles/companies/`, `agents/profiles/governments/`, `agents/profiles/regulators/`, `agents/profiles/consumers/`, `agents/profiles/suppliers/`, `agents/profiles/investors/`, `simulation/`, `institutions/`, `scenarios/`, `network/`, `models/`, `output/`, `notebooks/`, `tests/`, `data/runs/`
- [ ] `__init__.py` present in: `agents/`, `simulation/`, `models/`, `output/`, `tests/`
- [ ] `requirements.txt` includes (pinned to minor versions):
  ```
  openai>=1.30
  pydantic>=2.7
  httpx
  tenacity
  rich
  jupyter
  ipywidgets
  matplotlib
  pandas
  pytest
  pytest-asyncio
  nest-asyncio
  streamlit
  ```
- [ ] `python -c "from agents.base import BaseAgent"` runs without ImportError after `uv pip install -r requirements.txt`
- [ ] `.gitignore` excludes `__pycache__/`, `*.pyc`, `.venv/`, `data/runs/*.json`, `.env`
- [ ] `data/runs/.gitkeep` exists so the directory is tracked by git
- [ ] Running `pytest tests/` on the empty test directory exits cleanly (no collection errors)

### Technical notes

Keep all `__init__.py` files empty — do not put logic in them now. Circular import risk is high when models import from agents and agents import from models; clean `__init__.py` files prevent accidental circular imports at import time.

---

## Story 2: Core Pydantic Models — AgentProfile and AgentState

**Epic:** Models  
**Priority:** P0  
**Depends on:** Story 1

### What to build

Implement `models/agent_types.py` with the two most foundational models: `AgentProfile` (immutable, loaded from JSON) and `AgentState` (mutable, updated each round). Every other module in the system depends on these.

### Acceptance criteria

- [ ] `AgentType` enum defined as `str, Enum` with values: `company`, `government`, `regulator`, `consumer`, `supplier`, `investor`
- [ ] `AgentProfile` fields:
  ```python
  agent_id: str
  name: str
  agent_type: AgentType
  description: str
  objectives: list[str]
  constraints: list[str]
  data: dict[str, Any]          # role-specific financials, policy tools, etc.
  country: str                  # ISO-2 country code
  information_completeness: float = 1.0   # 0.0–1.0
  direct_partners: list[str] = []         # agent_ids of direct trading partners
  home_government_id: str | None = None   # for company/consumer/supplier agents
  ```
- [ ] `AgentProfile` is fully immutable (`model_config = ConfigDict(frozen=True)`)
- [ ] `classmethod AgentProfile.from_json(path: str) -> AgentProfile` loads via `Path(path).read_text()` then `model_validate(json.loads(...))`
- [ ] `AgentState` fields:
  ```python
  agent_id: str
  current_round: int = 0
  fear_greed_index: float = 5.0           # 0 (extreme fear) to 10 (extreme greed)
  capture_score: float = 0.0              # 0.0–1.0+, relevant for regulators/govts
  financial_health: float = 0.7          # 0.0–1.0
  active_actions: list[str] = []         # in-progress action IDs
  completed_actions: list[str] = []
  relationships: dict[str, float] = {}   # agent_id → trust score
  metrics: dict[str, float] = {}         # KPIs: revenue_change_pct, margin, etc.
  signals_sent: list[str] = []
  ```
- [ ] `AgentState` has `model_config = ConfigDict(extra="allow")` so resolver can attach computed fields without schema changes
- [ ] `classmethod AgentState.initial(profile: AgentProfile) -> AgentState` creates round-0 state: reads `profile.data.get("financial_health", 0.7)`, sets `fear_greed_index=5.0`, `capture_score=0.0`
- [ ] `AgentState.apply_updates(patch: dict)` applies resolver patches via `for k, v in patch.items(): setattr(self, k, v)` (or `model_copy(update=patch)`)
- [ ] Unit test: load minimal `AgentProfile` JSON fixture → assert all fields parse; mutate via `apply_updates` → assert round number incremented

### Technical notes

`data: dict[str, Any]` is intentionally untyped — it holds role-specific fields (financials for companies, fiscal rules for governments) that vary per profile. `AgentState.initial` should check `profile.data.get("fear_greed_index", 5.0)` to allow profiles to set a custom starting sentiment. Use `model_copy(update=patch)` not `setattr` for immutability-safe updates.

---

## Story 3: Core Pydantic Models — Action Enums and RoundResponse

**Epic:** Models  
**Priority:** P0  
**Depends on:** Story 2

### What to build

Define all 6 role-specific action enums and the `RoundResponse` model — the structured output every LLM call must produce. Also define `PublicSignal` and `PrivateIntent`.

### Acceptance criteria

- [ ] Six action enums as `str, Enum`:

  | Enum               | Values                                                                                                                                      |
  | ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------- |
  | `CompanyAction`    | `export_diversion`, `joint_venture`, `fdi`, `licensing`, `domestic_expansion`, `price_war`, `lobby_government`, `hedge`, `wait_and_observe` |
  | `GovernmentAction` | `retaliatory_tariff`, `subsidy`, `wto_dispute`, `trade_negotiation`, `capital_controls`, `stimulus`, `do_nothing`                           |
  | `RegulatorAction`  | `open_investigation`, `impose_provisional_duty`, `recommend_definitive_duty`, `reject_petition`, `issue_cautionary_note`                    |
  | `ConsumerAction`   | `switch_suppliers`, `stockpile`, `absorb_cost`, `pass_through_pricing`, `demand_subsidy`                                                    |
  | `SupplierAction`   | `raise_prices`, `hold_prices`, `lower_prices`, `diversify_customers`, `capacity_investment`, `negotiate_long_term`                          |
  | `InvestorAction`   | `buy`, `sell`, `short`, `fx_bet`, `sector_rotation`, `wait`                                                                                 |

- [ ] `PublicSignal` model:
  ```python
  from_agent: str
  to_agent: str | None   # None = broadcast to all
  content: str
  signal_type: str        # "announcement", "policy", "market_signal", etc.
  round: int
  ```
- [ ] `PrivateIntent` model:
  ```python
  content: str
  target_agent: str | None
  ```
- [ ] `RoundResponse` fields:
  ```python
  agent_id: str
  round: int
  primary_action: str             # coerced to valid action string by parser
  secondary_action: str | None
  assessment: str                 # narrative reasoning, max 500 chars
  confidence: float               # 0.0–1.0
  impact_areas: list[str]
  metrics_change: dict[str, float] = {}
  signals_to_ecosystem: list[PublicSignal] = []
  private_intent: PrivateIntent | None = None
  raw_llm_output: str | None = None
  is_fallback: bool = False
  ```
- [ ] `classmethod RoundResponse.fallback(agent_id: str, round: int) -> RoundResponse` returns a safe "wait_and_observe"/"wait" response with `confidence=0.3`, `assessment="[FALLBACK] LLM failed to produce valid response after retries."`, `is_fallback=True`
- [ ] Unit test: construct `RoundResponse` from dict → validates; `fallback()` → `is_fallback=True` and `confidence=0.3`

### Technical notes

`primary_action` is typed as `str` (not the enum) because the parser coerces the LLM output string to a valid action — the parser needs the agent's role to know which enum to validate against. The `signals_to_ecosystem` list is the agent's public broadcast to other agents next round. `private_intent` is NEVER shared with other agents — only the simulation observer (dashboard) sees it.

---

## Story 4: Core Pydantic Models — WorldState, RoundContext, RoundResolution

**Epic:** Models  
**Priority:** P0  
**Depends on:** Story 3

### What to build

Implement `models/world_state.py` and `models/events.py` with the god-view `WorldState`, the per-agent per-round input `RoundContext`, and the post-resolution `RoundResolution`.

### Acceptance criteria

- [ ] `WorldEvent` model in `models/events.py`:
  ```python
  event_type: str
  round: int
  description: str
  affected_agents: list[str]
  data: dict[str, Any] = {}
  ```
- [ ] Event type constants in `models/events.py`:
  ```python
  CAPTURE_TIPPING_POINT = "CAPTURE_TIPPING_POINT"
  MARKET_FLOOD = "MARKET_FLOOD"
  TRADE_WAR_ESCALATION = "TRADE_WAR_ESCALATION"
  SUPPLY_SHOCK = "SUPPLY_SHOCK"
  VALUATION_COLLAPSE = "VALUATION_COLLAPSE"
  DIPLOMATIC_BREAKDOWN = "DIPLOMATIC_BREAKDOWN"
  ```
- [ ] `MarketState` model in `models/market.py`:
  ```python
  commodity: str
  spot_price: float
  prev_price: float | None
  price_change_pct: float | None
  demand: float
  supply: float
  volume_cleared: float
  unmet_demand: float
  unmet_demand_pct: float
  price_history: list[float] = []
  ```
- [ ] `TradeRoute` model in `models/market.py`:
  ```python
  from_country: str
  to_country: str
  commodity: str
  volume: float
  tariff_rate: float
  friction: float   # 0.0–1.0, higher = more friction/cost
  ```
- [ ] `WorldState` model in `models/world_state.py`:
  ```python
  current_round: int = 0
  scenario_name: str
  agent_profiles: dict[str, AgentProfile]     # agent_id → profile
  agent_states: dict[str, AgentState]          # agent_id → mutable state
  market_states: dict[str, MarketState]        # commodity → MarketState
  trade_routes: list[TradeRoute]
  all_signals: list[PublicSignal]              # every public signal ever produced
  events: list[WorldEvent]
  round_responses: dict[int, dict[str, RoundResponse]]  # round → agent_id → response
  ```
- [ ] Helper methods on `WorldState`:
  - `get_agent_state(agent_id: str) -> AgentState`
  - `get_signals_for_round(round: int) -> list[PublicSignal]`
  - `get_responses_for_round(round: int) -> dict[str, RoundResponse]`
- [ ] `RoundContext` model:
  ```python
  agent_id: str
  round: int
  shock: dict[str, Any]
  visible_signals: list[PublicSignal]
  market_state: dict[str, MarketState]
  competitive_effects: dict[str, float]
  impacts_on_agent: dict[str, Any]
  own_state: AgentState
  capture_bias: str | None = None   # injected if agent is captured
  ```
- [ ] `RoundResolution` model:
  ```python
  round: int
  trade_flow_changes: list[TradeRoute]
  market_clearing: dict[str, MarketState]
  capture_updates: dict[str, float]           # agent_id → new capture_score
  valuation_changes: dict[str, float]         # agent_id → valuation % change
  sentiment_updates: dict[str, float]         # agent_id → new fear_greed_index
  conflicts: list[dict]
  agent_state_patches: dict[str, dict]        # agent_id → partial patch dict
  events: list[WorldEvent]
  ```
- [ ] Unit test: construct minimal `WorldState`, add a signal, retrieve via helper

### Technical notes

`RoundResolution.agent_state_patches` is intentionally `dict[str, dict]` (partial patches) not `dict[str, AgentState]`. The resolver produces only changed fields; the engine applies them via `agent.state.apply_updates(patch)`. This avoids the resolver needing to reconstruct full AgentState objects. `WorldState.round_responses` is the historical archive indexed by round number, enabling replay.

---

## Story 5: Core Pydantic Models — ShockScenario

**Epic:** Models  
**Priority:** P0  
**Depends on:** Story 2

### What to build

Implement `models/scenario.py` with `ShockScenario` — the external event that drives the entire simulation.

### Acceptance criteria

- [ ] `ShockScenario` fields:
  ```python
  id: str
  name: str
  description: str
  category: Literal["tariff", "supply_shock", "regulatory", "financial", "diplomatic", "natural_disaster"]
  severity: float                     # 0.0–1.0, validated
  affected_sectors: list[str]
  context: str                        # narrative paragraph for LLM prompts
  initial_market_impacts: dict[str, float] = {}  # commodity → price multiplier
  duration_rounds: int | None = None  # None = indefinite
  initiating_country: str | None = None
  initial_parameters: dict[str, Any] = {}    # tariff_rate_pct, target_country, etc.
  ```
- [ ] Field validator: `severity` in [0.0, 1.0] — raise `ValueError("severity must be between 0.0 and 1.0")` if not
- [ ] `classmethod ShockScenario.from_json(path: str) -> ShockScenario`
- [ ] Unit test: load `tariff_shock.json` fixture → asserts all fields parse; `severity=1.5` raises `ValueError`

### Technical notes

The `context` field is the most important — it gets injected verbatim into every agent's system prompt as the "ground truth" of what happened. Write it like a Reuters wire service brief: factual, present-tense, specific numbers. `initial_market_impacts` is applied by the engine on round 1 to set starting prices before any agent decisions.

---

## Story 6: Agent Profile JSON Files — Companies

**Epic:** Data / Agent Profiles  
**Priority:** P0  
**Depends on:** Story 2

### What to build

Create `agents/profiles/companies/tata_steel.json` and `agents/profiles/companies/jsw_steel.json` with realistic, research-grounded data. The differentiation between these two companies is critical for interesting simulation behavior.

### Acceptance criteria

- [ ] Both files validate against `AgentProfile.from_json()` without errors
- [ ] `tata_steel.json` data block (FY2024 sourced):
  ```json
  {
    "revenue_usd_bn": 22.0,
    "ebitda_margin_pct": 18.0,
    "us_export_volume_mt": 2100000,
    "cash_reserves_usd_bn": 4.2,
    "debt_to_equity": 0.6,
    "primary_markets": ["India", "Europe", "Southeast Asia"],
    "lobbying_budget_usd_mn": 50,
    "active_subsidiaries": [
      "Tata Steel UK",
      "NatSteel",
      "Tata Steel Netherlands"
    ],
    "financial_health": 0.82,
    "fear_greed_index": 5.5,
    "loss_aversion_multiplier": 2.0,
    "herd_tendency": 0.3,
    "risk_appetite": "moderate"
  }
  ```
- [ ] `tata_steel.json` objectives (at least 4): includes "Maintain global export diversification across 3+ markets", "Protect European operations during US tariff shock"
- [ ] `tata_steel.json` constraints (at least 3): includes "Board approval required for capex > $1Bn", "UK operations require separate regulatory compliance"
- [ ] `jsw_steel.json` data block:
  ```json
  {
    "revenue_usd_bn": 14.0,
    "ebitda_margin_pct": 15.0,
    "us_export_volume_mt": 800000,
    "cash_reserves_usd_bn": 1.8,
    "debt_to_equity": 1.1,
    "primary_markets": ["India", "US", "Middle East"],
    "lobbying_budget_usd_mn": 20,
    "active_subsidiaries": [],
    "financial_health": 0.65,
    "fear_greed_index": 4.5,
    "loss_aversion_multiplier": 2.5,
    "herd_tendency": 0.6,
    "risk_appetite": "conservative"
  }
  ```
- [ ] `jsw_steel.json` objectives: includes "Protect US market share as primary growth channel"
- [ ] `jsw_steel.json` constraints: includes "Debt covenants restrict new capex above $500M without board approval", "Higher US dependency means tariff shock is existential not manageable"
- [ ] Both profiles have `direct_partners: ["iron_ore", "gov_india"]` and `home_government_id: "gov_india"`

### Technical notes

The Tata/JSW differentiation is load-bearing: Tata has more options (reroute via UK operations, fall back on European markets), JSW has higher US exposure and less financial slack. This should produce divergent LLM decisions in the tariff shock scenario — Tata pivots, JSW panics. The `loss_aversion_multiplier` difference (2.0 vs 2.5) is subtle but important: JSW will overreact to losses relative to Tata.

---

## Story 7: Agent Profile JSON Files — All Other Agents

**Epic:** Data / Agent Profiles  
**Priority:** P0  
**Depends on:** Story 2

### What to build

Create all remaining agent profile JSON files for governments, regulator, consumer, supplier, and investors.

### Acceptance criteria

- [ ] `agents/profiles/governments/india.json`:
  ```json
  {
    "agent_id": "gov_india",
    "name": "Government of India (Ministry of Commerce)",
    "agent_type": "government",
    "country": "IN",
    "information_completeness": 0.95,
    "direct_partners": ["dgtr", "tata_steel", "jsw_steel"],
    "objectives": [
      "Protect domestic steel industry employment (500K+ jobs)",
      "Maintain WTO compliance while pursuing retaliation options",
      "Stabilize steel prices to prevent industrial cost inflation",
      "Diversify export markets to reduce US dependency"
    ],
    "constraints": [
      "WTO commitments limit retaliatory tariff rates",
      "Fiscal deficit ceiling at 6% GDP constrains subsidy scale",
      "DGTR investigation process has minimum 6-month duration"
    ],
    "data": {
      "fiscal_deficit_pct_gdp": 5.1,
      "wto_member": true,
      "free_trade_agreements": ["ASEAN", "UAE-CEPA", "Mauritius"],
      "diplomatic_status": {
        "US": "strategic_partner",
        "CN": "competitive_neutral"
      },
      "policy_tools": [
        "tariff",
        "subsidy",
        "export_incentive",
        "exchange_rate_intervention"
      ],
      "steel_sector_gdp_contribution_pct": 2.0,
      "financial_health": 0.75,
      "fear_greed_index": 4.0
    }
  }
  ```
- [ ] `agents/profiles/governments/us.json`: includes `trade_deficit_with_india_usd_bn: 35`, `domestic_steel_lobby_influence: 0.8`, `section_232_authority: true`, `diplomatic_status: {"IN": "strategic_partner", "CN": "adversarial"}`, `information_completeness: 1.0`
- [ ] `agents/profiles/regulators/dgtr.json`: role=regulator, data includes `jurisdiction: "India"`, `current_investigations: []`, `average_investigation_duration_months: 14`, `historical_duty_rate_range: [0, 30]`, `capture_vulnerability: 0.4`, `information_completeness: 0.85`
- [ ] `agents/profiles/consumers/industrial_steel.json`: role=consumer, data includes `annual_steel_consumption_mt: 45`, `import_dependency_pct: 30`, `price_sensitivity: 0.75`, `switching_lead_time_months: 3`
- [ ] `agents/profiles/suppliers/iron_ore.json`: role=supplier, data includes `annual_supply_capacity_mt: 300`, `price_per_ton_usd: 115`, `margin_pct: 22`, `contracted_volume_pct: 60`, `direct_partners: ["tata_steel", "jsw_steel"]`
- [ ] `agents/profiles/investors/fii_aggregate.json`: role=investor, data includes `aum_india_usd_bn: 180`, `steel_sector_allocation_pct: 4.2`, `sentiment_sensitivity: 0.85`, `information_completeness: 0.8`
- [ ] `agents/profiles/investors/retail_aggregate.json`: role=investor, data includes `aum_india_usd_bn: 45`, `steel_sector_allocation_pct: 6.1`, `sentiment_sensitivity: 0.95`, `information_completeness: 0.6`
- [ ] All 7 files load via `AgentProfile.from_json()` without validation errors

### Technical notes

`information_completeness` differences are intentional: US government sees everything (1.0), retail investors have the worst information (0.6). This drives realistic information asymmetry in the visibility filter. The `capture_vulnerability: 0.4` on DGTR is the key parameter the `CaptureEngine` uses to determine how quickly lobbying converts to capture score.

---

## Story 8: Scenario, Network, and Institution JSON Files

**Epic:** Data / Scenarios  
**Priority:** P0  
**Depends on:** Story 5

### What to build

Create the scenario files, trade network topology, and institution rule files that the engine loads.

### Acceptance criteria

- [ ] `scenarios/tariff_shock.json`:
  ```json
  {
    "id": "tariff_shock_us_india_2025",
    "name": "US 50% Tariff on Indian Steel",
    "category": "tariff",
    "severity": 0.85,
    "affected_sectors": ["steel", "manufacturing", "auto"],
    "initiating_country": "US",
    "context": "The United States has imposed a 50% ad valorem tariff on all steel imports from India effective immediately under Section 232 authority, citing national security concerns. Indian steel exports to the US, valued at approximately $1.8 billion annually, now face duties that effectively price them out of the US market. The move is expected to force Indian producers to divert 2+ million tons of steel to already-competitive Asian and European markets, compressing margins industry-wide.",
    "initial_market_impacts": { "steel_hrc": 0.72, "iron_ore": 0.95 },
    "initial_parameters": {
      "tariff_rate_pct": 50,
      "target_country": "IN",
      "imposing_country": "US",
      "affected_trade_value_usd_bn": 1.8
    }
  }
  ```
- [ ] `scenarios/antidumping_petition.json`: category="regulatory", severity=0.4, about domestic industry filing anti-dumping petition against Chinese steel, initiating_country="IN"
- [ ] `scenarios/supply_disruption.json`: category="supply_shock", severity=0.6, about iron ore export disruption from Australia affecting Indian steel input costs
- [ ] `network/steel_ecosystem.json`: JSON with `routes` array; routes must include:
  - `IN → US` steel, baseline_volume_mt=2100000, baseline_tariff_pct=25, friction=0.15
  - `IN → EU` steel, baseline_volume_mt=800000, baseline_tariff_pct=5, friction=0.2
  - `IN → ASEAN` steel, baseline_volume_mt=600000, baseline_tariff_pct=3, friction=0.1
  - `AU → IN` iron_ore, baseline_volume_mt=50000000, baseline_tariff_pct=2, friction=0.05
  - `CN → IN` steel, baseline_volume_mt=1500000, baseline_tariff_pct=12, friction=0.12
- [ ] `institutions/india.json`: includes `wto_obligations`, `min_investigation_period_months: 6`, `max_provisional_duty_pct: 30`, `fiscal_rules: {"deficit_ceiling_pct": 6.0}`
- [ ] `institutions/us.json`: includes `section_232_authority: true`, `wto_member: true`, `trade_remedy_agencies: ["USITC", "DOC"]`
- [ ] `ShockScenario.from_json("scenarios/tariff_shock.json")` loads without errors

### Technical notes

The `context` field is the most important content to get right — it gets injected verbatim into every agent's LLM prompt. Write it like a Reuters wire brief. The `initial_market_impacts` values mean: on round 1, `steel_hrc` price is multiplied by 0.72 (28% drop in India as exports are blocked), `iron_ore` barely moves (0.95). This creates an immediate crisis for companies that the LLM must respond to.

---

## Story 9: ResponseParser — All 6 Agent Response Schemas

**Epic:** Agents  
**Priority:** P0  
**Depends on:** Story 3

### What to build

Implement `agents/parser.py` with `ResponseParser` that validates raw LLM JSON output and returns a `RoundResponse`. The six agent-type-specific schemas here define exactly what the LLM must produce each round.

### Acceptance criteria

- [x] Six Pydantic validation models defined in `agents/parser.py` (inheriting from `BaseAgentResponse`):

  **`BaseAgentResponse`** (shared base):

  ```python
  action_id: str              # validated against available action list
  secondary_action_id: str | None = None
  reasoning: str              # min 20 chars, max 800 chars
  public_signal: str          # min 10 chars, max 300 chars — visible to all agents next round
  private_signal: str         # min 10 chars, max 300 chars — NEVER shared with other agents
  confidence: float           # 0.0–1.0
  metrics_change: dict[str, float] = {}
  ```

  **`CompanyResponse(BaseAgentResponse)`**:

  ```python
  target_markets: list[str]           # ISO-2 country codes
  capex_commitment_usd_mn: float = 0.0
  lobby_target: str | None = None     # regulator agent_id if lobbying
  lobby_amount_usd_mn: float = 0.0
  production_change_pct: float = 0.0  # -100 to 200
  export_volume_mt: float | None = None
  ```

  **`GovernmentResponse(BaseAgentResponse)`**:

  ```python
  policy_instrument: Literal["tariff", "subsidy", "quota", "export_ban", "bilateral_negotiation", "wto_dispute", "none"]
  tariff_rate_pct: float | None = None       # 0–300
  subsidy_amount_usd_mn: float | None = None
  target_country_iso: str | None = None
  wto_notification_status: Literal["not_required", "notified", "pending", "disputed"] = "not_required"
  political_feasibility: float               # 0.0–1.0
  retaliation_risk: float                    # 0.0–1.0
  ```

  **`RegulatorResponse(BaseAgentResponse)`**:

  ```python
  enforcement_action: Literal["investigation_open", "investigation_close", "fine_issued", "rule_proposed", "rule_finalized", "exemption_granted", "no_action"]
  fine_amount_usd_mn: float | None = None
  target_entity_id: str | None = None
  rule_scope: str | None = None
  independence_score: float   # 0.0–1.0 — watch for capture
  ```

  **`ConsumerResponse(BaseAgentResponse)`**:

  ```python
  purchase_decision: Literal["buy_domestic", "buy_imported", "delay_purchase", "substitute_product", "reduce_consumption", "bulk_stockpile"]
  volume_demand_mt: float
  max_price_usd_per_mt: float
  price_sensitivity: float    # 0.0–1.0
  ```

  **`SupplierResponse(BaseAgentResponse)`**:

  ```python
  supply_offer: Literal["increase_supply", "decrease_supply", "hold_supply", "redirect_to_new_market", "strategic_stockpile", "long_term_contract_offer"]
  volume_offered_mt: float
  min_price_usd_per_mt: float
  contract_length_months: int = 0   # 0 = spot
  destination_markets: list[str]
  ```

  **`InvestorResponse(BaseAgentResponse)`**:

  ```python
  investment_action: Literal["increase_long", "reduce_long", "open_short", "close_short", "rotate_sector", "hold", "exit_market"]
  position_changes: dict[str, float]           # agent_id → USD mn delta
  portfolio_allocation_pct: dict[str, float]   # agent_id → new %, must sum to 100 ± 0.5
  leverage_ratio: float = 1.0                  # 0–10
  macro_thesis: str                            # min 20 chars
  ```

- [x] `RESPONSE_MODELS: dict[str, type[BaseAgentResponse]]` registry mapping role strings to schema classes
- [x] `ResponseParser.parse(raw: str, agent_type: str, agent_state: dict, available_action_ids: list[str], attempt: int = 0) -> BaseAgentResponse` — full pipeline: strip fences → JSON parse → Pydantic validate → semantic constraints → return or raise `ParseError`
- [x] `_strip_fences(raw: str) -> str` — regex strips ` ```json ... ``` ` or ` ``` ... ``` `; fallback: `re.search(r'\{.*\}', raw, re.DOTALL)` to extract JSON from prose
- [x] Semantic constraint checks (raise `ParseError` with retry_prompt if violated):
  - `action_id` not in `available_action_ids`
  - Company: `capex_commitment_usd_mn + lobby_amount_usd_mn > 0.8 * agent_state["cash_usd_mn"]`
  - Investor: `sum(portfolio_allocation_pct.values())` not in [99.5, 100.5]
- [x] `ParseError(Exception)` carries `retry_prompt: str` (injected verbatim by BaseAgent) and `attempt: int`
- [x] On complete parse failure at max retries: caller uses `RoundResponse.fallback()` — parser itself always raises `ParseError`, never returns fallback
- [x] Coercion (log warning but don't fail): unknown `action_id` → `difflib.get_close_matches(action, valid, n=1, cutoff=0.6)` → substitute; `confidence` outside [0,1] → clamp; `assessment` > 500 chars → truncate with `...`
- [x] `ResponseParser` accumulates `parse_errors: list[str]` for session-level diagnostics
- [ ] Unit tests in `tests/test_parser.py`:
  - Valid JSON round-trips correctly
  - JSON inside code fences is extracted
  - Unknown action coerced to closest valid via difflib
  - Completely invalid JSON raises `ParseError`
  - Confidence outside [0,1] clamped silently
  - Investor portfolio not summing to 100 raises `ParseError`

### Technical notes

The retry prompt format (injected by BaseAgent on parse failure):

```
"Your previous response contained errors. Attempt {attempt+1} of 3.

Errors:
{numbered error list}

Your previous response:
---
{original_raw[:500]}
---

Resubmit corrected JSON only. No markdown, no explanation."
```

For action coercion, build the lookup at module init: `_VALID_ACTIONS = {role: set(action.value for action in ActionEnum)}`. The `difflib.get_close_matches` approach recovers from common LLM typos like "export_diversification" → "export_diversion" without crashing.

---

## Story 10: VisibilityFilter

**Epic:** Agents  
**Priority:** P0  
**Depends on:** Story 4

### What to build

Implement `agents/visibility.py` with `VisibilityFilter` — the information asymmetry engine. Every agent sees a different filtered view of the world each round.

### Acceptance criteria

- [x] `VisibilityFilter.get_visible_signals(world_state: WorldState, profile: AgentProfile, round: int) -> list[PublicSignal]` is the primary method
- [x] **Private intent NEVER included** — `PublicSignal` has no private fields; `PrivateIntent` objects are stripped at the `WorldState.all_signals` level (only `PublicSignal` objects are stored there)
- [x] **Information delay rule:** signals from agents in a different country have a 1-round delay (`signal.round <= current_round - 1`). Same-country agents: no delay (`signal.round == current_round - 1` is the previous round's signal, which is always visible)
- [x] **Must-keep signals** (always included regardless of completeness score):
  - Government agents: all signals from own-country agents
  - Company agents: signals from `profile.home_government_id` and `profile.direct_partners`
  - Regulator agents: signals from own-jurisdiction government
  - All agents: own signals (not visible to others as self, but available in own memory)
- [x] **Information completeness filter:** for non-must-keep signals, each signal included with probability = `profile.information_completeness`. Use `random.Random(seed=round * 1000 + hash(profile.agent_id) % 1000)` for deterministic, reproducible seeding per agent per round
- [x] `VisibilityFilter.get_competitive_effects(world_state: WorldState, profile: AgentProfile) -> dict[str, float]` — reads last round's `round_responses` and computes rule-based effects:
  - If competitor company chose `export_diversion` to same markets: add `{"competitor_diversion_pressure": 0.3}`
  - If government issued subsidy to competitor: add `{"competitor_subsidy_advantage": 0.2}`
  - If investor chose `sell` on this company: add `{"investor_sell_pressure": 0.4}`
- [ ] Unit tests in `tests/test_visibility.py`:
  - Cross-country signal delayed 1 round (not visible in same round it was produced)
  - Same-country signal visible next round (no delay)
  - Must-keep signal always present even at `information_completeness=0.1`
  - Private intent object never returned (only PublicSignal objects)
  - Determinism: same agent + same round + same seed = identical filtered list

### Technical notes

The deterministic seeding is critical for reproducibility. Use `rng = random.Random(round * 1000 + hash(profile.agent_id) % 1000)` then `rng.random() < completeness` per signal. Never use global `random.seed()` which would affect other modules. The `get_competitive_effects` method is the primary mechanism for competitive dynamics — when Tata Steel diverts exports to ASEAN, JSW Steel sees a `competitor_diversion_pressure` signal that influences its own decision.

---

## Story 11: PromptBuilder — All 6 Agent Type System Prompts

**Epic:** Agents  
**Priority:** P0  
**Depends on:** Stories 4, 10

### What to build

Implement `agents/prompts.py` with `PromptBuilder` that produces system prompts and round messages for all 6 agent types. This is the primary interface between simulation state and LLM reasoning.

### Acceptance criteria

- [x] `PromptBuilder.build_system_prompt(profile: AgentProfile, capture_bias: str | None = None) -> str`:
  - **Section A — Persona (always present):**

    ```
    You are {profile.name}, a {profile.agent_type} in the global steel/EV economy.

    Your objectives:
    1. {objective_1}
    2. {objective_2}
    ...

    Your constraints (you MUST respect these):
    1. {constraint_1}
    ...

    Behavioral profile:
    - Loss aversion: {loss_aversion_multiplier}× (you weight losses this much heavier than equivalent gains)
    - Risk appetite: {risk_appetite}
    - Herd tendency: {herd_tendency} (0=contrarian, 1=follows consensus)
    - Cultural orientation: power_distance={x}, uncertainty_avoidance={y}, long_term_orientation={z}
    ```

  - **Section B — Capture bias (conditional, appended when `capture_bias` is not None):**
    Subtle framing text from CaptureEngine (see Story 14). Not "you are captured" — realistic regulatory-speak.
  - Company prompt explicitly mentions: "Your fear-greed index is currently [X]/10. Below 4 = risk-averse. Above 7 = confident and may pursue aggressive actions."
  - Government prompt mentions capture score if > 0.3: "Note: You have received significant lobbying pressure from [agent]. This may influence your policy calculus."

- [x] `PromptBuilder.build_round_message(context: RoundContext, profile: AgentProfile, memory: list[RoundResponse]) -> str`:
      Assembles 7 ordered sections:
  1. **Round + Shock:** `=== ROUND {n} OF 5 — ECONOMIC SHOCK UPDATE ===\n{context.shock["context"]}`
  2. **Your Position:** financial_health, fear_greed_index, active_actions, metrics from `context.own_state`
  3. **Market Conditions:** prices and volumes from `context.market_state` as bullet list
  4. **Market Intelligence:** `context.visible_signals` labeled by source agent; if empty: "No prior signals available. You are deciding under full uncertainty."
  5. **Competitive Effects:** `context.competitive_effects` formatted as bullet list
  6. **Available Actions:** role-appropriate action list with one-line descriptions and costs (filtered to available actions only):
     - Example: "`export_diversion` — Reroute export volumes from US to EU/ASEAN. Requires 2–3 rounds to fully execute. Cost: 5–15% cash."
     - Locked actions shown as: "[LOCKED] `fdi` — Insufficient cash reserves ($1.2Bn < $2Bn required)"
  7. **Your Previous Decisions (last 2 rounds):** from `memory[-2:]` — enables evolving strategy
  8. **Response Format:** exact JSON schema the LLM must produce, with example response inline (not just field descriptions)
- [x] `PromptBuilder.get_available_actions(profile: AgentProfile, state: AgentState) -> list[dict]`:
      Returns list of `{"action_id": str, "available": bool, "reason": str | None}` applying constraint rules per role
- [ ] Unit test: build system prompt for each of 6 roles with mock profile → non-empty, contains agent name and objectives; build round message → all 8 sections present

### Technical notes

The **response format section** (section 8) is the most important for output quality. Always include an **inline example JSON response**, not just field descriptions. The example should be role-appropriate (use real action values) and demonstrate all required fields. The available actions filter is the key mechanism preventing the LLM from hallucinating impossible choices — never show an action the agent cannot take. The 2-round memory context enables "strategy evolution" rather than the LLM treating each round as independent.

---

## Story 12: BaseAgent — LLM Interface and Retry Logic

**Epic:** Agents  
**Priority:** P0  
**Depends on:** Stories 9, 11

### What to build

Implement `agents/base.py` with `BaseAgent` — the only class in the codebase that makes external LLM API calls. Everything else is pure Python.

### Acceptance criteria

- [x] `BaseAgent.__init__(profile: AgentProfile, model: str = "moonshotai/kimi-k2")`:
  - Stores `profile`, initializes `state = AgentState.initial(profile)`
  - Creates `async_client = AsyncOpenAI(api_key=os.environ["OPENROUTER_API_KEY"], base_url="https://openrouter.ai/api/v1")`
  - Initializes `memory: list[RoundResponse] = []`
  - Initializes `parser = ResponseParser()`, `prompt_builder = PromptBuilder()`
- [x] `async BaseAgent.act_async(context: RoundContext) -> RoundResponse`:

  ```python
  MAX_RETRIES = 2
  system_prompt = prompt_builder.build_system_prompt(profile, context.capture_bias)
  user_message = prompt_builder.build_round_message(context, profile, memory)
  messages = [
      {"role": "system", "content": system_prompt},
      {"role": "user",   "content": user_message}
  ]

  for attempt in range(MAX_RETRIES + 1):
      raw = await async_client.chat.completions.create(
          model=self.model,
          messages=messages,
          response_format={"type": "json_object"},
          temperature=0.7,
          max_tokens=2000,
      ).choices[0].message.content

      try:
          parsed = parser.parse(raw, profile.agent_type, state_dict, available_ids, attempt)
          response = _to_round_response(parsed, context.round, raw)
          memory.append(response)
          return response
      except ParseError as e:
          if attempt == MAX_RETRIES:
              fallback = RoundResponse.fallback(profile.agent_id, context.round)
              memory.append(fallback)
              return fallback
          messages.append({"role": "assistant", "content": raw})
          messages.append({"role": "user", "content": e.retry_prompt})
  ```

- [x] `BaseAgent.act(context: RoundContext) -> RoundResponse` — sync wrapper using `asyncio.run(self.act_async(context))`; handles Jupyter's running event loop via `nest_asyncio`
- [x] API error handling in `act_async`: catch `openai.RateLimitError` → `await asyncio.sleep(2 ** attempt)` and retry; catch all other `openai.APIError` → use fallback at max retries
- [x] `BaseAgent.update_state(patch: dict)` — calls `self.state.apply_updates(patch)`
- [x] `BaseAgent.agent_id` property returns `self.profile.agent_id`
- [ ] Unit test (mock `AsyncOpenAI`): verify retry called on `APIError`; verify fallback returned after 2 failures; verify memory accumulates across calls

### Technical notes

Use `nest_asyncio.apply()` once in `__init__` to handle Jupyter's event loop. Set `temperature=0.7` — low enough for consistent structured output, high enough for varied reasoning. The `response_format={"type": "json_object"}` is supported by most OpenRouter models and dramatically reduces parse failures — always use it. Pass the last 2 rounds of the agent's own `memory` through `build_round_message` to enable strategy evolution.

---

## Story 13: MarketClearing

**Epic:** Simulation  
**Priority:** P0  
**Depends on:** Story 4

### What to build

Implement `simulation/market.py` with `MarketClearing` — deterministic double-auction supply/demand matching and price discovery.

### Acceptance criteria

- [ ] Pydantic models `SupplyOffer` and `DemandRequest`:

  ```python
  class SupplyOffer(BaseModel):
      agent_id: str
      product: str          # "steel_hrc", "iron_ore", "ev_battery"
      volume_mt: float      # > 0
      min_price_usd_per_mt: float  # > 0

  class DemandRequest(BaseModel):
      agent_id: str
      product: str
      volume_mt: float
      max_price_usd_per_mt: float
  ```

- [ ] `MarketClearing.clear_product(product: str, supply_offers: list[SupplyOffer], demand_requests: list[DemandRequest], round_number: int) -> MarketState`:
  - Runs double-auction: sort supply ascending by ask, sort demand descending by bid
  - Greedy matching: while `bid >= ask`, match at `clearing_price = (ask + bid) / 2.0`
  - Apply tariff per route (via `TradeNetwork` lookup): `effective_price = clearing_price * (1 + tariff_rate / 100)`. If `effective_price > buyer's max_price`, skip this buyer.
  - Volume cleared = min(supply_remaining, demand_remaining) per match
  - `unmet_demand = max(0, total_demand - volume_cleared)`
  - `price_change_pct = (new_price - prev_price) / prev_price * 100` (None in round 1)
  - Computes `consumer_surplus` and `producer_surplus`
- [ ] `MarketClearing.clear_all_products(all_offers, all_requests, round_number) -> dict[str, MarketState]` groups by product and calls `clear_product` for each
- [ ] Price change capped at ±25% per round
- [ ] No randomness — fully deterministic
- [ ] Unit tests in `tests/test_market.py`:
  - Excess supply (supply > demand) → price decreases
  - Excess demand → price increases
  - Price change cap at 25% enforced
  - `unmet_demand_pct` correct calculation
  - Tariff pushing effective price above buyer max → no trade cleared
  - Round 1 `price_change_pct` is `None` not 0.0

### Technical notes

The asymmetric price adjustment (supply surplus → 0.1× magnitude, demand surplus → 0.15× magnitude) models the empirical observation that commodity prices spike faster than they fall. The 25% cap prevents runaway feedback loops. The double-auction midpoint price `(ask + bid) / 2` is the simplest fair mechanism — no need for a more complex algorithm. Floating point residuals: treat remaining volume `< 1e-6 MT` as exhausted.

---

## Story 14: CaptureEngine

**Epic:** Simulation  
**Priority:** P1  
**Depends on:** Story 4

### What to build

Implement `simulation/capture.py` with `CaptureEngine` — the lobbying-to-regulatory-capture mechanism that makes regulators progressively biased toward their largest lobbyists.

### Acceptance criteria

- [ ] `CaptureState` model:
  ```python
  regulator_id: str
  capture_vulnerability: float         # from profile.data["capture_vulnerability"]
  cumulative_lobbying_usd_mn: float = 0.0  # post-decay running total
  capture_score: float = 0.0          # 0.0 = independent, 1.0+ = captured
  is_captured: bool = False
  captured_by_company_id: str | None = None
  capture_score_history: list[float] = []
  ```
- [ ] Constants: `CAPTURE_THRESHOLD = 0.70`, `RELEASE_THRESHOLD = 0.45` (hysteresis), `DECAY_RATE = 0.15`, `VULNERABILITY_SCALE = 100.0`
- [ ] `CaptureEngine.initialize_regulator(regulator_id: str, capture_vulnerability: float) -> CaptureState`
- [ ] `CaptureEngine.process_round(lobbying_actions: list[LobbyingAction], round_number: int) -> tuple[dict[str, CaptureState], list[WorldEvent]]`:
  1. Apply decay: `cumulative_T = cumulative_{T-1} * (1 - 0.15)` (before adding new lobbying)
  2. Add new lobbying: `cumulative_T += sum(amounts for this regulator this round)`
  3. Recompute: `capture_score = cumulative / (vulnerability * 100)`
  4. Flip detection with hysteresis:
     - If not captured and `score > 0.70`: flip to captured → emit `CAPTURE_TIPPING_POINT` event
     - If captured and `score < 0.45`: flip to independent → emit event
- [ ] `CaptureEngine.get_bias_prompt(regulator_id: str) -> str | None` — returns calibrated bias text based on capture_score band:
  - 0.70–0.85: mild framing ("stakeholder operational concerns deserve balanced consideration")
  - 0.85–1.00: stronger framing ("regulatory actions that damage competitive position carry systemic risk")
  - 1.00+: max capture ("institutional relationships have deeply informed your understanding")
  - Returns `None` if not captured
- [ ] `LobbyingAction` is extracted from `CompanyResponse.lobby_target` and `lobby_amount_usd_mn` fields
- [ ] Unit tests: two rounds of lobbying → capture_score increases; one round no lobbying → decay applied; tipping point event fires at threshold crossing; release event fires at release threshold

### Technical notes

The `CaptureEngine` itself does NOT modify prompts — it only updates scores and returns bias text. The `SimulationEngine` calls `get_bias_prompt()` and passes it into `RoundContext.capture_bias`, which `PromptBuilder.build_system_prompt()` injects as Section B. This keeps concerns separated. The 15% decay means capture from a single lobbying event fades over ~6 rounds (`0.85^6 ≈ 0.37`), preventing permanent capture from a one-time spend.

---

## Story 15: TradeNetwork

**Epic:** Simulation  
**Priority:** P0  
**Depends on:** Story 4

### What to build

Implement `simulation/trade.py` with `TradeNetwork` — loads the trade network topology from JSON and recalculates trade flows each round based on policy changes.

### Acceptance criteria

- [ ] `TradeNetwork.load(path: str) -> TradeNetwork` — loads `network/steel_ecosystem.json`, returns instance with `routes: list[TradeRoute]`
- [ ] `TradeNetwork.apply_policy(action: str, actor_country: str, target_country: str, commodity: str, magnitude: float) -> None`:
  - `retaliatory_tariff`: increase `tariff_rate` on matching route by `magnitude`
  - `subsidy`: reduce effective tariff (add negative offset, floor at 0)
  - `capital_controls`: increase `friction` by 0.1 on all routes from `actor_country`
- [ ] `TradeNetwork.recalculate_flows(market_states: dict[str, MarketState]) -> list[TradeRoute]`:
  - Each route's volume = `baseline_volume * (1 - tariff_rate/100) * (1 - friction) * price_attractiveness`
  - `price_attractiveness = target_market_price / global_average_price` (higher-price markets get more volume)
  - Clamped to [0, baseline_volume * 2.0] to prevent unrealistic spikes
- [ ] `TradeNetwork.get_routes(from_country: str | None = None, commodity: str | None = None) -> list[TradeRoute]`
- [ ] `TradeNetwork.detect_events(previous_routes: list[TradeRoute], current_routes: list[TradeRoute]) -> list[WorldEvent]`:
  - `MARKET_FLOOD`: any single route volume increase > 40% in one round
  - `TRADE_WAR_ESCALATION`: tariffs increased on routes in both directions between two countries in the same round
- [ ] Unit test: applying `retaliatory_tariff` reduces route volume in next recalculation; `MARKET_FLOOD` fires at correct threshold

### Technical notes

The `price_attractiveness_factor` is the key driver for export diversion realism. When the US market becomes expensive (tariff shock), India→US route volume drops automatically. Simultaneously, India→ASEAN volume increases because ASEAN prices are relatively higher. This creates the realistic outcome that export diversion floods third markets and compresses prices there too — without any explicit code to handle it.

---

## Story 16: SentimentEngine

**Epic:** Simulation  
**Priority:** P1  
**Depends on:** Story 4

### What to build

Implement `simulation/sentiment.py` with `SentimentEngine` — updates fear-greed indices (0–10) for all agents using Kahneman-Tversky prospect theory and herding behavior.

### Acceptance criteria

- [ ] `AgentOutcome` model:
  ```python
  agent_id: str
  agent_type: str
  revenue_change_pct: float
  market_share_change_pct: float
  action_succeeded: bool      # primary action achieved intended effect
  action_conflicted: bool     # another agent directly countered this action
  loss_aversion_multiplier: float
  herd_tendency: float
  prev_sentiment: float
  ```
- [ ] `SentimentEngine.compute_sentiment(outcome: AgentOutcome, peer_summary: PeerBehaviorSummary) -> SentimentResult`:
  - **Step 1 — Prospect theory utility:**

    ```python
    def _kt_utility(change_pct, loss_aversion):
        if change_pct >= 0:  return change_pct          # gains: linear
        else:               return -loss_aversion * abs(change_pct)  # losses: amplified

    revenue_utility = _kt_utility(revenue_change_pct, lam)
    share_utility   = _kt_utility(share_change_pct, lam)
    action_utility  = 5.0 if (succeeded and not conflicted) else (-5.0 * lam if conflicted else 0)
    raw_utility     = 0.50 * revenue_utility + 0.25 * share_utility + 0.25 * action_utility
    ```

  - **Step 2 — Normalize via tanh:**
    ```python
    import math
    normalized_delta = 5.0 * math.tanh(raw_utility / 5.0)
    ```
  - **Step 3 — Herd adjustment:**
    ```python
    peer_greed_signal = (peer_summary.aggressive_pct - 0.5) * 2   # [-1, +1]
    herd_delta = herd_tendency * 1.0 * peer_greed_signal
    ```
  - **Step 4 — Momentum + regression to mean:**
    ```python
    new_sentiment = 0.85 * prev_sentiment + 0.15 * 5.0 + normalized_delta + herd_delta
    new_sentiment = max(0.0, min(10.0, new_sentiment))
    ```

- [ ] `SentimentEngine.compute_all(outcomes: list[AgentOutcome], peer_summary: PeerBehaviorSummary) -> dict[str, float]` — returns `{agent_id: new_fear_greed_index}`
- [ ] `SentimentEngine.build_peer_summary(responses: list, aggressive_action_ids: set) -> PeerBehaviorSummary`
- [ ] `SentimentEngine.get_market_fear_greed(agent_states: dict) -> float` — weighted average (by `information_completeness`) across all agents
- [ ] Round 1 initializes `prev_sentiment = 5.0` for all agents
- [ ] Unit test: loss with `loss_aversion=2.5` → larger negative delta than equivalent gain; peer all-defensive → high-herd agent pulled toward fear; regression-to-mean prevents permanent extremes

### Technical notes

The regression-to-mean (15% pull toward 5.0 each round via `0.85 * score + 0.15 * 5.0`) prevents the simulation from locking into permanent extreme fear or greed after 3–4 rounds. This is the most important calibration decision — if simulation behavior feels flat, reduce the momentum weight; if it oscillates too wildly, increase it. The fear-greed value feeds directly into `PromptBuilder.build_system_prompt()`, making it one of the most impactful behavioral levers.

---

## Story 17: StateResolver — 10-Step Resolution Pipeline

**Epic:** Simulation  
**Priority:** P0  
**Depends on:** Stories 13, 14, 15, 16

### What to build

Implement `simulation/resolver.py` with `StateResolver` — the deterministic brain that takes all agent responses and produces a `RoundResolution`. **Order of steps is load-bearing and must not be changed.**

### Acceptance criteria

- [ ] `StateResolver.__init__(market: MarketClearing, capture: CaptureEngine, trade: TradeNetwork, sentiment: SentimentEngine)`
- [ ] `StateResolver.resolve(responses: dict[str, RoundResponse], world_state: WorldState, profiles: dict[str, AgentProfile]) -> RoundResolution`:

  **Step 1 — Extract and apply policy changes:**
  - Read `GovernmentResponse.policy_instrument` + target + magnitude from all government responses
  - Call `trade.apply_policy()` for each tariff/subsidy action

  **Step 2 — Recalculate trade flows:**
  - Call `trade.recalculate_flows(world_state.market_states)` → `RoundResolution.trade_flow_changes`

  **Step 3 — Market clearing:**
  - Extract supply offers from `SupplierResponse.volume_offered_mt` and `min_price_usd_per_mt`
  - Extract demand from `ConsumerResponse.volume_demand_mt` and `max_price_usd_per_mt`
  - Add government stimulus (+10% demand) and stockpile (+15% demand) effects
  - Call `market.clear_all_products()` → `RoundResolution.market_clearing`

  **Step 4 — Capture updates:**
  - Extract `LobbyingAction`s from `CompanyResponse.lobby_target` and `lobby_amount_usd_mn`
  - Call `capture.process_round()` → `RoundResolution.capture_updates`

  **Step 5 — Investor valuation changes:**
  - For each `InvestorResponse.position_changes`: positive = buy → increase target company valuation by `amount * 0.02`; negative = sell/short → decrease by `amount * 0.02` (short: `* 0.04`)
  - Store in `RoundResolution.valuation_changes`

  **Step 6 — Conflict detection:**
  - Two companies targeting same market for `export_diversion` → each gets 30% volume penalty → log to `conflicts`

  **Step 7 — Competitive effects:**
  - Company `price_war` action → competitor's margin reduced 8%
  - Company `export_diversion` to same market → target market price drops 5%
  - Store in `resolution.competitive_effects` keyed by affected agent_id

  **Step 8 — Sentiment updates:**
  - Build `AgentOutcome` per agent from market clearing results and actions
  - Call `sentiment.compute_all()` → `RoundResolution.sentiment_updates`

  **Step 9 — Assemble per-agent state patches:**
  - Merge financial changes, capture score updates, sentiment updates, valuation changes into per-agent dicts
  - If two steps patch same field, later step wins

  **Step 10 — Collect and return events:**
  - Gather events from `capture.process_round()`, `trade.detect_events()`, custom threshold checks
  - Store in `RoundResolution.events`

- [ ] Unit tests in `tests/test_resolver.py`:
  - Government tariff action flows through to reduced trade route volume
  - Lobbying action increases capture score
  - Investor sell produces negative valuation change
  - Two companies targeting same market triggers conflict in resolution
  - All 10 steps produce non-None outputs (no silent failures)

### Technical notes

The resolution order is intentional: policy must be applied to trade before flows are recalculated; flows must be recalculated before market clearing (prices depend on flows); market clearing before sentiment (sentiment reacts to price changes). Wrapping each step in try/except and logging the partial `RoundResolution` on error makes debugging much faster.

---

## Story 18: SimulationEngine and run_scenario()

**Epic:** Simulation  
**Priority:** P0  
**Depends on:** Stories 12, 17

### What to build

Implement `simulation/engine.py` with `SimulationEngine` and the `run_scenario()` convenience function. This is the top-level orchestrator of the entire system.

### Acceptance criteria

- [ ] `SimulationEngine.__init__(scenario: ShockScenario, agents: list[BaseAgent], trade_network: TradeNetwork, market: MarketClearing, capture: CaptureEngine, sentiment: SentimentEngine)`:
  - Initializes `world_state = WorldState(...)` from scenario and agent profiles
  - Applies `scenario.initial_market_impacts` to `world_state.market_states` on round 1
  - Initializes `resolver = StateResolver(market, capture, trade_network, sentiment)`
- [ ] `SimulationEngine.run(rounds: int = 5) -> SimulationResult` — the 4-phase round loop:
  ```
  for round = 1 to N:
    Phase 1: Build RoundContext per agent (PromptBuilder + VisibilityFilter)
             → inject capture_bias from CaptureEngine.get_bias_prompt()
    Phase 2: Execute all agents in parallel → ThreadPoolExecutor
    Phase 3: StateResolver.resolve() → RoundResolution
    Phase 4: Apply patches to AgentStates, update WorldState, print round summary
  ```
- [ ] **Parallel execution:** Use `concurrent.futures.ThreadPoolExecutor(max_workers=min(len(agents), 8))`. Submit all agent `.act()` calls simultaneously. Collect with `as_completed()`. Per-agent timeout: 30 seconds. On timeout: use `RoundResponse.fallback()`.
- [ ] After each round: rich console output via `rich.table.Table` showing round number, each agent's action + confidence + truncated assessment (80 chars)
- [ ] `WorldState` updated each round: append new `PublicSignal`s to `all_signals`, append responses to `round_responses[round]`, apply `agent_state_patches` to all agent states, advance `world_state.current_round`
- [ ] Convergence check: if all agents chose `wait_and_observe`/`do_nothing`/`wait`/`hold` for 2 consecutive rounds, break early and log convergence
- [ ] `run_scenario(scenario_path: str, agent_profile_paths: list[str], institution_paths: list[str] = [], network_path: str = "network/steel_ecosystem.json", rounds: int = 3, model: str = "moonshotai/kimi-k2") -> SimulationResult` — convenience function that loads all JSON files and calls `engine.run()`
- [ ] Engine logs start time, end time, total API calls, any fallback incidents to console

### Technical notes

Use `ThreadPoolExecutor` (not `asyncio`) for the parallel execution — the OpenAI SDK's sync client is thread-safe, and notebook environments have unreliable asyncio event loop handling at the outer loop level. Each `BaseAgent.act()` call internally uses `asyncio.run()` for its own retry loop. `max_workers=min(len(agents), 8)` avoids hammering the API with too many simultaneous requests. The 30-second per-agent timeout is generous; most calls complete in 3–8 seconds.

---

## Story 19: SimulationResult and Output Formatters

**Epic:** Output  
**Priority:** P0  
**Depends on:** Story 18

### What to build

Implement `output/results.py` with `SimulationResult` — the queryable container for completed simulation data — and `output/formatters.py` with rich terminal and notebook output formatters.

### Acceptance criteria

- [ ] `SimulationResult` fields:
  ```python
  scenario: ShockScenario
  rounds_completed: int
  world_state: WorldState
  metadata: dict   # model_used, duration_seconds, timestamp, total_fallbacks
  ```
- [ ] Query methods on `SimulationResult`:
  - `get_round(n: int) -> dict[str, RoundResponse]` — all agent responses for round n
  - `get_agent_history(agent_id: str) -> list[RoundResponse]` — all responses across all rounds
  - `get_events(event_type: str | None = None) -> list[WorldEvent]` — optionally filtered by type
  - `get_capture_timeline() -> dict[str, list[float]]` — agent_id → capture scores per round
  - `get_price_timeline(commodity: str) -> list[float]` — clearing prices per round
  - `get_trade_flow_evolution() -> dict[str, list[float]]` — route_key → volume per round
- [ ] `SimulationResult.save(path: str)` — serializes via `model.model_dump(mode="json")`; handles datetime → isoformat
- [ ] `classmethod SimulationResult.load(path: str) -> SimulationResult` — deserializes from JSON
- [ ] Save/load round-trips correctly: `SimulationResult.load(path).rounds_completed == original.rounds_completed`
- [ ] `output/formatters.py` — `RichFormatter` class:
  - `print_round_summary(round_n, responses, resolution)` — rich table per round (agent, action, confidence, assessment preview, fear-greed)
  - `print_final_summary(result)` — final state table across all agents + events fired
- [ ] Unit test: save minimal result to `$TMPDIR`, load it back, assert round count and agent IDs preserved

### Technical notes

The `save/load` round-trip is critical for demo workflow: run the simulation once, save results, then explore in notebook without re-running LLM calls. Use `SimulationResult.model_dump(mode="json")` which serializes everything to JSON-compatible primitives. All `get_*` methods are O(n) scans — fine for ≤10 agents × ≤20 rounds. Use `rich.table.Table` and `rich.console.Console` for formatted terminal output.

---

## Story 20: Unit Tests — Four Test Files

**Epic:** Testing  
**Priority:** P1  
**Depends on:** Stories 9, 10, 13, 17

### What to build

Implement all four test files with shared fixtures. All tests must be LLM-free.

### Acceptance criteria

- [ ] `tests/conftest.py` provides:
  - `minimal_company_profile()` fixture (valid `AgentProfile` for a company role)
  - `minimal_government_profile()` fixture
  - `minimal_world_state(round=1)` fixture (two agents, steel_hrc market, one trade route)
  - `sample_round_response(agent_id, action="export_diversion")` fixture
  - `sample_tariff_shock()` fixture
- [ ] `tests/test_parser.py` (8 tests):
  - Valid JSON parses to `CompanyResponse` correctly
  - JSON wrapped in ` ```json ... ``` ` fences → extracted and parsed
  - Unknown action `"export_diversification"` → coerced to `"export_diversion"` via difflib
  - Completely invalid JSON string → raises `ParseError`
  - `confidence=-0.2` → clamped to 0.0 silently
  - `confidence=1.5` → clamped to 1.0 silently
  - `assessment` over 500 chars → truncated to 500 with `...`
  - Company capex > 80% cash → raises `ParseError` with constraint violation message
- [ ] `tests/test_market.py` (6 tests):
  - Excess supply (2× demand) → price decreases
  - Excess demand (2× supply) → price increases
  - Price change capped at 25% when delta would be 50%
  - `unmet_demand_pct` = `(demand - cleared) / demand`
  - Tariff-inclusive effective price above buyer max → no trade cleared
  - Round 1 `price_change_pct` is `None`, not 0.0
- [ ] `tests/test_visibility.py` (5 tests):
  - Signal from different country in round 2 not visible to an agent in round 2 (1-round delay)
  - Signal from same country in round 1 visible to same-country agent in round 2
  - Agent's own government's signal always in result even with `information_completeness=0.1`
  - `PrivateIntent` object never appears in returned signals
  - Same agent + same round + same `random.Random` seed → identical filtered list
- [ ] `tests/test_resolver.py` (5 tests):
  - Government choosing `retaliatory_tariff` → `TradeRoute.tariff_rate` increases in `trade_flow_changes`
  - Company choosing `lobby_government` → `capture_updates[regulator_id]` increases
  - Investor choosing `sell` → negative entry in `valuation_changes`
  - Two companies targeting same market for `export_diversion` → `conflicts` list non-empty
  - `WorldEvent` list non-empty after resolution with lobbying above capture threshold
- [ ] `pytest tests/ -v` exits with code 0 in < 30 seconds
- [ ] Zero LLM calls in any test (use `unittest.mock.patch("agents.base.openai.AsyncOpenAI")`)

### Technical notes

Write market tests first — they have zero dependencies and give the fastest feedback loop. Use `pytest.fixture(scope="module")` for profiles (expensive to construct) and `scope="function"` for mutable world state (avoid test pollution). The conftest fixtures should use realistic data matching the actual JSON profiles, not minimal stubs — this gives integration confidence.

---

## Story 21: Demo Notebook — 01_tariff_shock_demo.ipynb

**Epic:** Output / Demo  
**Priority:** P0  
**Depends on:** Stories 18, 19

### What to build

Create `notebooks/01_tariff_shock_demo.ipynb` — the primary demo artifact that must run end-to-end and tell a coherent economic story.

### Acceptance criteria

- [ ] **Cell 1 — Markdown:** Title ("US Steel Tariff Shock: A Multi-Agent Economic Simulation"), scenario overview, "what you'll see" preview with bullet points
- [ ] **Cell 2 — Setup:**
  ```python
  DEMO_MODE = False  # Set True to load pre-saved results without API key
  # Verify env var set (mask value)
  # Print package versions
  import nest_asyncio; nest_asyncio.apply()
  ```
- [ ] **Cell 3 — Load scenario:** Print scenario name, severity, context paragraph, initial market impacts dict
- [ ] **Cell 4 — Load agents:** Rich table with columns: Agent Name | Role | Country | Key Metric | Info Completeness
- [ ] **Cell 5 — Run simulation:**
  ```python
  if DEMO_MODE:
      result = SimulationResult.load("data/runs/tariff_shock_demo.json")
  else:
      result = run_scenario("scenarios/tariff_shock.json", [...all agent paths...], rounds=3)
      result.save("data/runs/tariff_shock_demo.json")
  ```
  Real-time output streams to cell as rounds complete.
- [ ] **Cell 6 — Round-by-round table:** Per-round, per-agent action + confidence; bold high-confidence decisions (> 0.7)
- [ ] **Cell 7 — Price timeline chart:** matplotlib line chart, `steel_hrc` and `iron_ore` prices per round. Y-axis: USD/ton. Clear title, legend.
- [ ] **Cell 8 — Trade flow evolution:** Line chart showing India→US volume collapse and India→SEA + India→EU increase. Demonstrates the export diversion thesis.
- [ ] **Cell 9 — Fear-greed timeline:** Per-agent fear-greed index across rounds. Each agent a different color. Horizontal reference lines at 4.0 (fear boundary) and 7.0 (greed boundary).
- [ ] **Cell 10 — Capture score timeline:** If lobbying occurred, show capture score progression for DGTR. Threshold line at 0.7. Else: print "No regulatory capture activity detected."
- [ ] **Cell 11 — Events log:** Formatted list of all `WorldEvent`s: round, type, description, affected agents
- [ ] **Cell 12 — Agent deep dive (Tata Steel):** Full `assessment` narrative per round showing how reasoning evolved
- [ ] **Cell 13 — Markdown conclusion:** Economic takeaways from the simulation
- [ ] All cells execute without error on `Run All`; total time < 5 minutes
- [ ] Notebook is pre-run with outputs saved (demo-able without API key when `DEMO_MODE=True`)
- [ ] Charts use `plt.style.use("seaborn-v0_8-darkgrid")` for clean academic presentation look

### Technical notes

Pre-run the notebook with `moonshotai/kimi-k2` (cheapest model) and save outputs + the `data/runs/tariff_shock_demo.json` results file. Commit both to the repo so the MBA presentation can be demoed without an API key. For real-time streaming output in Cell 5, use `IPython.display.clear_output(wait=True)` + rich console inside the engine's per-round hook.

---

## Story 22: Smoke Test and Integration Harness

**Epic:** Testing  
**Priority:** P1  
**Depends on:** Story 18

### What to build

Create `tests/test_smoke.py` with a live smoke test (requires API key) and a fixture-based integration test (no API key needed) that exercises the full pipeline with saved LLM responses.

### Acceptance criteria

- [ ] `test_smoke_2x2`: runs `run_scenario` with only `tata_steel.json` and `india.json`, 2 rounds, `model="moonshotai/kimi-k2"`; asserts `result.rounds_completed == 2`, both agent IDs present; `@pytest.mark.skipif(not os.environ.get("OPENROUTER_API_KEY"), reason="No API key")`
- [ ] `tests/fixtures/tariff_shock_2round_responses.json`: committed to repo with verbatim LLM JSON responses for 2 rounds × 7 agents (captured from a real run via `RoundResponse.raw_llm_output`)
- [ ] `test_integration_replay`: loads fixture file, patches `BaseAgent.act` to return pre-parsed `RoundResponse` objects, runs full engine including resolver, market clearing, capture, and sentiment; asserts all modules produce output; no API calls
- [ ] Both tests run in < 60 seconds total
- [ ] `pytest tests/test_smoke.py -k "integration"` runs only the replay test (CI-safe)

### Technical notes

The fixture file is the most valuable testing artifact — it lets you develop resolver, market, and sentiment logic without burning API credits. Generate it once from a real run with `--log-cli-level=DEBUG`. Use realistic responses (not minimal stubs) — the goal is integration confidence. Check it in alongside the rest of the code.

---

## Story 23: Streamlit Dashboard (P2 — Optional)

**Epic:** Output  
**Priority:** P2  
**Depends on:** Story 19

### What to build

Implement `output/dashboard.py` — an interactive Streamlit app for exploring simulation results. Implement only after P0+P1 complete and time permits.

### Acceptance criteria

- [ ] `streamlit run output/dashboard.py` launches without error
- [ ] Sidebar: file picker to load a `SimulationResult` JSON; scenario name + metadata displayed
- [ ] Tab 1 "Market": price and trade flow timelines; commodity selector
- [ ] Tab 2 "Agents": agent selector; action history, fear-greed timeline, metrics table per round
- [ ] Tab 3 "Events": table of all `WorldEvent`s; filterable by event type
- [ ] Tab 4 "Capture": capture score timelines for all government/regulator agents; threshold line at 0.7
- [ ] All charts use `st.plotly_chart` for interactivity
- [ ] Handles no-file-loaded state gracefully ("Load a simulation result to begin")
- [ ] Display only — does NOT trigger new simulation runs

### Technical notes

The Streamlit dashboard is significantly more impressive than a static notebook for an in-person MBA presentation. If the presentation date allows, prioritize this in week 3. Use `pd.DataFrame` to feed Streamlit charts — it handles column labeling automatically. Access all result data through `SimulationResult` query methods, not internal `WorldState` attributes.

---

## Implementation Checklist (Quick Reference)

| Story | Module                                                                          | Priority | Status |
| ----- | ------------------------------------------------------------------------------- | -------- | ------ |
| 1     | Project scaffold + requirements.txt                                             | P0       | done   |
| 2     | `models/agent_types.py` — AgentProfile, AgentState                              | P0       | done   |
| 3     | `models/agent_types.py` — action enums, RoundResponse                           | P0       | done   |
| 4     | `models/world_state.py`, `models/events.py`, `models/market.py`                 | P0       | done   |
| 5     | `models/scenario.py`                                                            | P0       | done   |
| 6     | `agents/profiles/companies/*.json`                                              | P0       | done   |
| 7     | `agents/profiles/{governments,regulators,consumers,suppliers,investors}/*.json` | P0       | done   |
| 8     | `scenarios/*.json`, `network/*.json`, `institutions/*.json`                     | P0       | done   |
| 9     | `agents/parser.py` — ResponseParser + 6 schemas                                 | P0       |        |
| 10    | `agents/visibility.py` — VisibilityFilter                                       | P0       |        |
| 11    | `agents/prompts.py` — PromptBuilder                                             | P0       |        |
| 12    | `agents/base.py` — BaseAgent                                                    | P0       |        |
| 13    | `simulation/market.py` — MarketClearing                                         | P0       | done   |
| 14    | `simulation/capture.py` — CaptureEngine                                         | P1       | done   |
| 15    | `simulation/trade.py` — TradeNetwork                                            | P0       | done   |
| 16    | `simulation/sentiment.py` — SentimentEngine                                     | P1       | done   |
| 17    | `simulation/resolver.py` — StateResolver                                        | P0       | done   |
| 18    | `simulation/engine.py` — SimulationEngine + run_scenario()                      | P0       | done   |
| 19    | `output/results.py` + `output/formatters.py`                                    | P0       | done   |
| 20    | `tests/test_*.py` — all 4 test files                                            | P1       | done   |
| 21    | `notebooks/01_tariff_shock_demo.ipynb`                                          | P0       | done   |
| 22    | `tests/test_smoke.py` — smoke + integration                                     | P1       | done   |
| 23    | `output/dashboard.py` — Streamlit                                               | P2       | skip   |
