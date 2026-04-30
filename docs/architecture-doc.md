# Application Architecture

> **Purpose:** This is the main coding reference. It defines every module, class, data flow, and interface in the system. A developer should be able to read this document and build the application without ambiguity about what goes where.

---

## 1. Design philosophy

Three rules govern every architectural decision:

**LLMs do qualitative reasoning, code does quantitative math.** When Tata Steel decides whether to pursue FDI or export diversion — that's an LLM call. When the engine computes whether two exporters flooding ASEAN collapses prices — that's Python math. Never ask the LLM to compute market prices. Never hardcode strategic decisions.

**JSON in, JSON out.** Every boundary between modules speaks JSON. Agent profiles are JSON. Scenarios are JSON. LLM responses are structured JSON. Simulation results are JSON. This makes the entire system inspectable, debuggable, and serializable at every step.

**Configuration over code.** Adding a new agent, scenario, or institutional rule set should require zero code changes — only new JSON files. The simulation engine should be able to run any combination of agents against any scenario without modification.

---

## 2. Directory structure

```
mba/
├── agents/                          # Agent layer
│   ├── base.py                      # BaseAgent class — LLM interface + memory
│   ├── prompts.py                   # PromptBuilder — assembles per-round context
│   ├── parser.py                    # ResponseParser — validates LLM JSON output
│   ├── visibility.py                # VisibilityFilter — who sees what
│   └── profiles/                    # Agent instance data (JSON, no code)
│       ├── companies/
│       │   ├── tata_steel.json
│       │   └── jsw_steel.json
│       ├── governments/
│       │   ├── india.json
│       │   └── us.json
│       ├── regulators/
│       │   └── dgtr.json
│       ├── consumers/
│       │   └── industrial_steel.json
│       ├── suppliers/
│       │   └── iron_ore.json
│       └── investors/
│           ├── fii_aggregate.json
│           └── retail_aggregate.json
│
├── simulation/                      # Engine layer
│   ├── engine.py                    # SimulationEngine — orchestrates rounds
│   ├── resolver.py                  # StateResolver — post-round consequence computation
│   ├── market.py                    # MarketClearing — supply/demand price discovery
│   ├── capture.py                   # CaptureEngine — lobbying accumulation, integrity thresholds
│   ├── trade.py                     # TradeNetwork — multi-country trade flow routing
│   └── sentiment.py                 # SentimentEngine — fear-greed updates across all agents
│
├── institutions/                    # Institutional rules (JSON, no code)
│   ├── india.json                   # India's rules: enforcement, transaction costs, CPI
│   ├── us.json
│   ├── eu.json
│   ├── asean.json
│   └── wto_constraints.json         # WTO rules that apply globally
│
├── scenarios/                       # Shock definitions (JSON, no code)
│   ├── tariff_shock_us_india.json
│   ├── ev_disruption.json
│   └── chinese_steel_dumping.json
│
├── network/                         # Trade network topology (JSON, no code)
│   └── steel_ecosystem.json         # Nodes = countries, edges = trade routes with friction
│
├── models/                          # Data classes / Pydantic models
│   ├── agent_types.py               # AgentProfile, AgentState, RoundResponse
│   ├── scenario.py                  # ShockScenario
│   ├── world_state.py               # WorldState — the god-view of the simulation
│   ├── market.py                    # MarketClearing result types
│   └── events.py                    # SimulationEvent — logged events for dashboard
│
├── output/                          # Output layer
│   ├── results.py                   # SimulationResult — query + persistence
│   ├── formatters.py                # Rich terminal + notebook display
│   └── dashboard.py                 # Optional: Streamlit dashboard for live demo
│
├── notebooks/                       # Demo + presentation notebooks
│   ├── 01_tariff_shock_demo.ipynb
│   ├── 02_ev_disruption_demo.ipynb
│   └── 99_presentation_deck.ipynb   # Notebook that generates presentation visuals
│
├── data/                            # Generated results (gitignored)
│   └── runs/
│       ├── tariff_shock_2025_run1.json
│       └── ...
│
├── tests/                           # Test suite
│   ├── test_parser.py               # Response parsing + validation
│   ├── test_resolver.py             # State resolution math
│   ├── test_market.py               # Market clearing logic
│   └── test_visibility.py           # Information filter correctness
│
├── requirements.txt
├── CLAUDE.md                        # Claude Code guidance
└── README.md
```

---

## 3. Layer architecture

### Layer 1: Data layer (JSON only, no code)

Everything the simulation needs to *configure* a run lives in JSON files. The principle: if a researcher wants to simulate a different industry, they edit JSON files — they never touch Python.

**Agent profiles** (`agents/profiles/`) define who each agent is. Schema defined in Agent Architecture Specification. One JSON file per agent instance. The engine loads all profiles listed in the run configuration.

**Scenarios** (`scenarios/`) define the external shock. Schema:
```json
{
  "id": "tariff_shock_us_india_2025",
  "name": "US 50% Tariff on Indian Exports",
  "description": "On August 7, 2025, the US imposed...",
  "category": "tariff",
  "severity": "extreme",
  "affected_sectors": ["steel", "automotive", "pharma", "textiles"],
  "context": "Extended background for agent reasoning...",
  "initial_parameters": {
    "tariff_rate_pct": 50,
    "target_country": "IN",
    "imposing_country": "US",
    "affected_trade_value_usd_bn": 87,
    "exempted_sectors": ["pharma", "semiconductors"]
  }
}
```

**Institutions** (`institutions/`) define the rules of each country's operating environment. These are the "game board" that agents play on:
```json
{
  "country_code": "IN",
  "name": "India",
  "enforcement_probability": 0.6,
  "corruption_perception_index": 39,
  "ease_of_doing_business_rank": 63,
  "transaction_cost_multiplier": 1.4,
  "ip_protection_strength": "moderate",
  "trade_agreements": ["WTO", "SAARC", "BRICS", "India-UAE_CEPA"],
  "fdi_restrictions": {
    "defense": "max_74pct_foreign",
    "media": "max_49pct_foreign",
    "multi_brand_retail": "max_51pct_with_conditions"
  },
  "regulatory_bodies": ["CCI", "SEBI", "DGTR", "RBI"]
}
```

**Trade network** (`network/`) defines the multi-country trade graph. Nodes are countries, edges are trade routes with friction parameters:
```json
{
  "network_id": "steel_global",
  "nodes": [
    { "id": "IN", "name": "India", "institution_ref": "institutions/india.json" },
    { "id": "US", "name": "United States", "institution_ref": "institutions/us.json" },
    { "id": "CN", "name": "China", "institution_ref": "institutions/china.json" },
    { "id": "EU", "name": "European Union", "institution_ref": "institutions/eu.json" },
    { "id": "ASEAN", "name": "ASEAN Bloc", "institution_ref": "institutions/asean.json" }
  ],
  "edges": [
    {
      "from": "IN", "to": "US",
      "product": "steel",
      "base_volume_mt": 1200000,
      "base_price_usd_per_mt": 650,
      "tariff_rate_pct": 25,
      "logistics_cost_usd_per_mt": 45,
      "institutional_friction": 1.2
    }
  ]
}
```

### Layer 2: Agent layer (LLM interface)

This layer owns the conversation with the LLM. Four modules, each with a single responsibility.

**`BaseAgent`** (`agents/base.py`) — The core agent class. One instance per actor in the simulation.

```python
class BaseAgent:
    """
    Wraps an LLM to act as a specific ecosystem actor.

    Owns:
    - profile: AgentProfile (loaded from JSON, immutable during run)
    - state: AgentState (mutable, updated each round)
    - memory: list[RoundResponse] (append-only, agent's complete history)

    Does NOT own:
    - Prompt assembly (delegated to PromptBuilder)
    - Response parsing (delegated to ResponseParser)
    - State resolution (engine's job after all agents act)
    """

    def __init__(self, profile_path: str, model: str = "claude-sonnet-4-6"):
        self.profile = AgentProfile.load(profile_path)
        self.state = AgentState.initial(self.profile)
        self.memory = []
        self.model = model
        self._client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ["OPENROUTER_API_KEY"]
        )

    def act(self, round_context: RoundContext) -> RoundResponse:
        """
        Called once per round by the SimulationEngine.
        1. Build prompt from context
        2. Call LLM
        3. Parse + validate response
        4. Append to memory
        5. Return structured response
        """
        prompt = PromptBuilder.build(self.profile, self.state, round_context)
        raw = self._call_llm(prompt)
        response = ResponseParser.parse(raw, self.profile.agent_type)
        self.memory.append(response)
        return response

    def update_state(self, resolved_state: dict):
        """
        Called by engine AFTER state resolution.
        Updates this agent's state with engine-computed consequences.
        """
        self.state.apply_updates(resolved_state)
```

**`PromptBuilder`** (`agents/prompts.py`) — Assembles the full prompt for each agent each round. This is where the Interaction Protocol's "Phase 1: State Assembly" lives in code.

```python
class PromptBuilder:
    @staticmethod
    def build(profile: AgentProfile, state: AgentState, ctx: RoundContext) -> str:
        """
        Assembles:
        1. System prompt (from agent type template + profile data)
        2. Round context (shock + visible signals + market data)
        3. Agent's current state
        4. Available action menu (filtered by constraints)
        5. Output format instruction
        """
        sections = [
            PromptBuilder._system_prompt(profile, state),
            PromptBuilder._shock_context(ctx.shock, ctx.round_number),
            PromptBuilder._visible_signals(ctx.public_signals),
            PromptBuilder._market_data(ctx.market_state),
            PromptBuilder._competitive_intelligence(ctx.competitive_effects),
            PromptBuilder._engine_computed_impacts(ctx.impacts_on_agent),
            PromptBuilder._current_state(state),
            PromptBuilder._available_actions(profile, state),
            PromptBuilder._output_format(profile.agent_type),
        ]
        return "\n\n".join(sections)
```

**`ResponseParser`** (`agents/parser.py`) — Validates LLM output against the expected schema. Handles retries for malformed responses.

```python
class ResponseParser:
    SCHEMAS = {
        "company": CompanyResponseSchema,
        "government": GovernmentResponseSchema,
        "regulator": RegulatorResponseSchema,
        "consumer": ConsumerResponseSchema,
        "supplier": SupplierResponseSchema,
        "investor": InvestorResponseSchema,
    }

    @staticmethod
    def parse(raw_text: str, agent_type: str) -> RoundResponse:
        """
        1. Extract JSON from LLM response (handle markdown fences)
        2. Validate against agent-type-specific schema
        3. Check constraint violations (e.g., spending > 80% cash)
        4. Return typed RoundResponse or raise ValidationError
        """
        json_str = ResponseParser._extract_json(raw_text)
        data = json.loads(json_str)
        schema = ResponseParser.SCHEMAS[agent_type]
        validated = schema.model_validate(data)
        return RoundResponse.from_validated(validated)
```

**`VisibilityFilter`** (`agents/visibility.py`) — Implements the information asymmetry rules from the Interaction Protocol. Given the full world state, produces a filtered view for each agent.

```python
class VisibilityFilter:
    @staticmethod
    def filter_for_agent(
        agent: BaseAgent,
        all_signals: list[AgentSignal],
        world_state: WorldState
    ) -> list[AgentSignal]:
        """
        Applies:
        1. Public-only filter (strip private_* fields)
        2. Visibility matrix (who can see whom)
        3. Information delay (distant agents = 1 round lag)
        4. Information completeness (low-info agents see fewer signals)
        5. Must-keep rules (always see own government, direct partners)
        """
        visible = []
        for signal in all_signals:
            if not VisibilityFilter._can_see(agent, signal, world_state):
                continue
            delay = VisibilityFilter._get_delay(agent, signal.source)
            if delay > 0 and signal.round > world_state.current_round - delay:
                continue  # too recent, apply delay
            public_signal = signal.strip_private()
            visible.append(public_signal)

        visible = VisibilityFilter._apply_completeness_filter(agent, visible)
        return visible
```

### Layer 3: Engine layer (orchestration + resolution)

This layer runs the simulation loop and computes consequences. No LLM calls here — pure deterministic Python.

**`SimulationEngine`** (`simulation/engine.py`) — The main orchestrator. Implements the 4-phase round loop.

```python
class SimulationEngine:
    def __init__(
        self,
        scenario_path: str,
        agent_paths: list[str],
        institution_paths: list[str],
        network_path: str,
        model: str = "claude-sonnet-4-6",
        rounds: int = 5
    ):
        self.scenario = ShockScenario.load(scenario_path)
        self.agents = [BaseAgent(p, model=model) for p in agent_paths]
        self.institutions = {
            i["country_code"]: i
            for p in institution_paths
            for i in [json.load(open(p))]
        }
        self.trade_network = TradeNetwork.load(network_path)
        self.world_state = WorldState.initial(
            self.agents, self.scenario, self.institutions, self.trade_network
        )
        self.rounds = rounds
        self.resolver = StateResolver(self.world_state)
        self.history = []

    def run(self) -> SimulationResult:
        for round_num in range(1, self.rounds + 1):
            self.world_state.current_round = round_num

            # Phase 1: State assembly
            round_contexts = {}
            for agent in self.agents:
                visible = VisibilityFilter.filter_for_agent(
                    agent, self.world_state.all_signals, self.world_state
                )
                ctx = RoundContext(
                    round_number=round_num,
                    shock=self.scenario,
                    public_signals=visible,
                    market_state=self.world_state.market_state,
                    competitive_effects=self.resolver.get_competitive_effects(agent),
                    impacts_on_agent=self.resolver.get_impacts(agent)
                )
                round_contexts[agent.profile.agent_id] = ctx

            # Phase 2: Agent execution (parallel-safe)
            round_responses = {}
            for agent in self.agents:
                ctx = round_contexts[agent.profile.agent_id]
                response = agent.act(ctx)
                round_responses[agent.profile.agent_id] = response

            # Phase 3: State resolution
            resolved = self.resolver.resolve_round(round_responses)

            # Apply resolved state back to agents
            for agent in self.agents:
                agent.update_state(resolved.agent_updates[agent.profile.agent_id])

            # Update world state
            self.world_state.apply_round_resolution(resolved)

            # Phase 4: Round output
            snapshot = self.world_state.snapshot()
            self.history.append(snapshot)

            # Check convergence
            if self._check_convergence():
                break

        return SimulationResult(
            scenario=self.scenario,
            agents=[a.profile for a in self.agents],
            rounds=self.history,
            events=self.world_state.events
        )
```

**`StateResolver`** (`simulation/resolver.py`) — The brain of post-round computation. Owns all the deterministic consequence logic.

```python
class StateResolver:
    """
    After all agents act, this class computes what actually happens.
    Every method here is pure math — no LLM calls.
    """

    def __init__(self, world_state: WorldState):
        self.world = world_state
        self.market = MarketClearing(world_state)
        self.capture = CaptureEngine(world_state)
        self.trade = TradeNetwork(world_state.trade_network)
        self.sentiment = SentimentEngine()

    def resolve_round(self, responses: dict[str, RoundResponse]) -> RoundResolution:
        """
        Orchestrates all resolution steps in order.
        Order matters: policy effects before market clearing,
        market clearing before sentiment update.
        """
        resolution = RoundResolution()

        # 1. Extract and apply policy changes (tariffs, subsidies, regulations)
        policy_changes = self._extract_policy_actions(responses)
        self.trade.apply_policy_changes(policy_changes)

        # 2. Resolve trade flow rerouting
        trade_flows = self.trade.recalculate_flows()
        resolution.trade_flow_updates = trade_flows

        # 3. Resolve market clearing (supply vs demand → realized prices)
        clearing = self.market.clear(responses, trade_flows)
        resolution.market_clearing = clearing

        # 4. Resolve lobbying → capture score updates
        capture_updates = self.capture.update(responses)
        resolution.capture_updates = capture_updates

        # 5. Resolve investor actions → valuation changes
        valuations = self._compute_valuations(responses, clearing)
        resolution.valuation_changes = valuations

        # 6. Resolve action conflicts
        conflicts = self._resolve_conflicts(responses)
        resolution.conflicts = conflicts

        # 7. Compute competitive effects for next round
        resolution.competitive_effects = self._compute_competitive_effects(
            responses, clearing
        )

        # 8. Update fear-greed for all agents
        for agent_id, response in responses.items():
            agent_outcome = self._compute_agent_outcome(agent_id, clearing, valuations)
            fg_update = self.sentiment.update_fear_greed(
                agent_id, agent_outcome, self.world
            )
            resolution.sentiment_updates[agent_id] = fg_update

        # 9. Compute per-agent state updates
        for agent_id in responses:
            resolution.agent_updates[agent_id] = self._compute_agent_state_update(
                agent_id, resolution
            )

        # 10. Log events (capture tipping points, market floods, etc.)
        resolution.events = self._detect_events(resolution)

        return resolution
```

**`MarketClearing`** (`simulation/market.py`) — Supply-demand matching and price discovery.

**`CaptureEngine`** (`simulation/capture.py`) — Lobbying accumulation and integrity threshold logic.

**`TradeNetwork`** (`simulation/trade.py`) — Multi-country trade flow graph with friction-based routing.

**`SentimentEngine`** (`simulation/sentiment.py`) — Universal fear-greed index computation across all agent types.

### Layer 4: Output layer

**`SimulationResult`** (`output/results.py`) — Query interface for simulation results.

```python
class SimulationResult:
    def get_round(self, n: int) -> RoundSnapshot: ...
    def get_agent_history(self, agent_id: str) -> list[RoundResponse]: ...
    def get_events(self, event_type: str = None) -> list[SimulationEvent]: ...
    def get_capture_timeline(self) -> dict[str, list[float]]: ...
    def get_price_timeline(self) -> list[float]: ...
    def get_trade_flow_evolution(self) -> dict: ...
    def save(self, path: str): ...

    @classmethod
    def load(cls, path: str) -> "SimulationResult": ...
```

---

## 4. Data models

All data flows through typed models. Using Pydantic for validation.

### Core types (`models/agent_types.py`)

```python
from pydantic import BaseModel
from typing import Optional
from enum import Enum

class AgentType(str, Enum):
    COMPANY = "company"
    GOVERNMENT = "government"
    REGULATOR = "regulator"
    CONSUMER = "consumer"
    SUPPLIER = "supplier"
    INVESTOR = "investor"

class AgentProfile(BaseModel):
    """Loaded from JSON. Immutable during simulation."""
    agent_id: str
    name: str
    agent_type: AgentType
    # ... all fields from Agent Architecture Spec

    @classmethod
    def load(cls, path: str) -> "AgentProfile":
        return cls.model_validate_json(Path(path).read_text())

class AgentState(BaseModel):
    """Mutable per-round state. Updated by engine after resolution."""
    current_round: int = 0
    fear_greed_index: float = 5.0
    # ... all state fields per agent type

    @classmethod
    def initial(cls, profile: AgentProfile) -> "AgentState":
        """Create initial state from profile defaults."""
        ...

    def apply_updates(self, updates: dict):
        """Merge engine-computed updates into state."""
        for key, value in updates.items():
            setattr(self, key, value)

class RoundResponse(BaseModel):
    """Structured LLM output after parsing + validation."""
    agent_id: str
    round: int
    primary_action: ActionDecision
    secondary_action: Optional[ActionDecision]
    assessment: AgentAssessment
    signals_to_ecosystem: EcosystemSignals
    # ... agent-type-specific fields

class ActionDecision(BaseModel):
    action: str
    target_market: Optional[str]
    investment_amount_usd_mn: float = 0
    rationale: str

class EcosystemSignals(BaseModel):
    public: str   # Other agents see this
    private: str  # Only simulation observer sees this
```

### World state (`models/world_state.py`)

```python
class WorldState(BaseModel):
    """
    The god-view. Engine reads and writes this.
    No agent ever sees the full world state.
    """
    current_round: int = 0
    scenario: ShockScenario
    agents: dict[str, AgentState]
    market_state: MarketState
    trade_network: TradeNetworkState
    institutional_rules: dict[str, InstitutionRules]
    diplomatic_states: dict[tuple[str, str], DiplomaticState]
    all_signals: list[AgentSignal]  # every public+private signal ever produced
    events: list[SimulationEvent]   # logged events for dashboard

    def snapshot(self) -> RoundSnapshot:
        """Deep copy of current state for history."""
        return RoundSnapshot(
            round=self.current_round,
            state=self.model_copy(deep=True)
        )

    def apply_round_resolution(self, resolution: RoundResolution):
        """Apply all computed consequences to world state."""
        self.market_state = resolution.market_clearing
        self.trade_network.apply_flow_updates(resolution.trade_flow_updates)
        for event in resolution.events:
            self.events.append(event)
        # Collect all public signals from this round
        for agent_id, response in resolution.responses.items():
            self.all_signals.append(AgentSignal(
                source_agent_id=agent_id,
                round=self.current_round,
                public=response.signals_to_ecosystem.public,
                private=response.signals_to_ecosystem.private
            ))
```

---

## 5. Key interfaces (contracts between modules)

### RoundContext — what the engine passes to each agent

```python
class RoundContext(BaseModel):
    """
    Built by SimulationEngine for each agent, each round.
    This is the agent's entire "world view" for this round.
    """
    round_number: int
    shock: ShockScenario                    # the external event
    public_signals: list[AgentSignal]       # filtered by VisibilityFilter
    market_state: MarketState               # prices, volumes, S/D ratio
    competitive_effects: dict               # what competitors did (engine-computed)
    impacts_on_agent: dict                  # revenue/cost changes from policies
```

### RoundResolution — what the engine computes after all agents act

```python
class RoundResolution(BaseModel):
    """
    Output of StateResolver.resolve_round().
    Contains all computed consequences for one round.
    """
    responses: dict[str, RoundResponse]           # raw agent responses
    market_clearing: MarketState                   # realized prices + volumes
    trade_flow_updates: TradeFlowChanges           # route-level volume shifts
    capture_updates: dict[str, CaptureState]       # regulator integrity changes
    valuation_changes: dict[str, float]            # company valuation % change
    sentiment_updates: dict[str, float]            # fear-greed index per agent
    competitive_effects: dict[str, dict]           # per-agent competitive impact
    conflicts: list[ConflictResolution]            # resolved action conflicts
    agent_updates: dict[str, dict]                 # per-agent state patches
    events: list[SimulationEvent]                  # dashboard-worthy events
```

---

## 6. LLM backend configuration

The system uses the OpenAI SDK pointed at OpenRouter, which provides access to multiple LLM providers through a single API.

```python
# Environment
OPENROUTER_API_KEY = os.environ["OPENROUTER_API_KEY"]

# Default model hierarchy
DEFAULT_MODELS = {
    "fast": "moonshotai/kimi-k2",            # agent calls during development
    "standard": "claude-sonnet-4-6",          # production agent calls
    "deep": "claude-opus-4-6",                # complex reasoning (optional)
}

# Client initialization (in BaseAgent.__init__)
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY
)

# LLM call pattern (in BaseAgent._call_llm)
response = client.chat.completions.create(
    model=self.model,
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": round_context_prompt}
    ],
    temperature=0.7,       # some randomness for realistic variation
    max_tokens=2000,       # enough for structured JSON response
    response_format={"type": "json_object"}  # enforce JSON output
)
```

**Model selection per agent type:** Different agent types can use different models. Government and company agents benefit from deeper reasoning (`claude-sonnet-4-6`), while consumer and supplier agents with simpler decision spaces can use faster models (`kimi-k2`) to save cost and time.

---

## 7. Execution flow — running a scenario end to end

### 7.1 Via convenience function

```python
from simulation.engine import run_scenario

result = run_scenario(
    scenario="scenarios/tariff_shock_us_india.json",
    agents=[
        "agents/profiles/companies/tata_steel.json",
        "agents/profiles/companies/jsw_steel.json",
        "agents/profiles/governments/india.json",
        "agents/profiles/governments/us.json",
        "agents/profiles/regulators/dgtr.json",
        "agents/profiles/consumers/industrial_steel.json",
        "agents/profiles/suppliers/iron_ore.json",
        "agents/profiles/investors/fii_aggregate.json",
    ],
    institutions=[
        "institutions/india.json",
        "institutions/us.json",
        "institutions/eu.json",
        "institutions/asean.json",
    ],
    network="network/steel_ecosystem.json",
    model="claude-sonnet-4-6",
    rounds=5,
)

result.save("data/runs/tariff_shock_run1.json")
```

### 7.2 Via notebook (primary demo path)

```python
# Cell 1: Setup
from simulation.engine import SimulationEngine
from output.formatters import display_round, display_summary

engine = SimulationEngine(
    scenario_path="scenarios/tariff_shock_us_india.json",
    agent_paths=[...],
    institution_paths=[...],
    network_path="network/steel_ecosystem.json",
    rounds=5
)

# Cell 2: Run
result = engine.run()

# Cell 3: Explore
display_round(result, round=2)              # detailed round view
display_summary(result)                      # cross-round summary table
result.get_capture_timeline()                # regulator integrity over time
result.get_agent_history("tata_steel")       # one agent's decision path
result.get_events("CAPTURE_TIPPING_POINT")   # specific event type
```

---

## 8. Error handling strategy

**LLM failures** — the most likely failure mode. The LLM may return malformed JSON, violate constraints, or refuse to respond in character.

```python
# In BaseAgent.act():
MAX_RETRIES = 2

for attempt in range(MAX_RETRIES + 1):
    try:
        raw = self._call_llm(prompt)
        response = ResponseParser.parse(raw, self.profile.agent_type)
        # Validate constraints
        ConstraintChecker.validate(response, self.profile, self.state)
        return response
    except JSONParseError:
        if attempt < MAX_RETRIES:
            prompt += "\n\nYour previous response was not valid JSON. Respond ONLY with a JSON object."
            continue
        return self._fallback_response()  # safe default action
    except ConstraintViolation as e:
        if attempt < MAX_RETRIES:
            prompt += f"\n\nConstraint violated: {e}. Choose a different action."
            continue
        return self._fallback_response()
    except Exception:
        return self._fallback_response()

def _fallback_response(self) -> RoundResponse:
    """
    Safe default: 'wait and observe' with neutral sentiment.
    Logged as a fallback so the dashboard can flag it.
    """
    return RoundResponse(
        agent_id=self.profile.agent_id,
        round=self.state.current_round,
        primary_action=ActionDecision(
            action="wait_and_observe",
            rationale="[FALLBACK] LLM failed to produce valid response"
        ),
        ...
    )
```

**Resolution errors** — deterministic code, so these are bugs. Fail fast with clear error messages. Wrap each resolver step in try/catch and log the partial resolution state for debugging.

**Data loading errors** — validate all JSON against Pydantic models at load time. Fail before the simulation starts, not during round 3.

---

## 9. Performance and cost considerations

**API costs per run** — the dominant cost. Budget estimate:

| Component | Calls per round | Rounds | Total calls | Est. cost |
|---|---|---|---|---|
| 8 agents × 1 LLM call each | 8 | 5 | 40 | ~$2-4 (Sonnet) |
| Retry calls (est. 10% failure) | ~1 | 5 | ~4 | ~$0.20 |
| **Total per run** | | | ~44 | **~$2-4** |

**Parallelization** — Phase 2 (agent execution) is embarrassingly parallel. All 8 agents can make LLM calls simultaneously since they operate on last round's state. Use `asyncio.gather()` or `concurrent.futures.ThreadPoolExecutor`:

```python
import asyncio

async def execute_agents_parallel(agents, contexts):
    tasks = [
        agent.act_async(contexts[agent.profile.agent_id])
        for agent in agents
    ]
    return await asyncio.gather(*tasks)
```

This cuts round execution time from ~40s (sequential, 8 × ~5s per call) to ~5-6s (parallel).

**State resolution** is pure Python math — negligible time (<100ms per round). No optimization needed.

---

## 10. How to extend

### Add a new agent type

1. Define the response schema in `models/agent_types.py`
2. Add the system prompt template in `agents/prompts.py`
3. Add visibility rules in `agents/visibility.py`
4. Add resolution logic for new interaction channels in `simulation/resolver.py`
5. Register the schema in `ResponseParser.SCHEMAS`
6. Create a JSON profile in the appropriate `agents/profiles/` subdirectory

### Add a new scenario

1. Create a JSON file in `scenarios/` following the schema
2. That's it — the engine loads any scenario without code changes

### Add a new country to the trade network

1. Create an institution JSON in `institutions/`
2. Add the node and edges to the relevant `network/*.json`
3. Optionally create a government agent profile in `agents/profiles/governments/`

### Add a new interaction channel

1. Define the data flow in the Interaction Protocol document
2. Add extraction logic in `StateResolver._extract_*` methods
3. Add resolution logic as a new method in `StateResolver`
4. Update `PromptBuilder` to include the new channel's signals in agent context
5. Update `VisibilityFilter` if the new channel has asymmetric visibility

### Switch LLM provider

Change the model string in `run_scenario()` or `BaseAgent(model=...)`. Any model available on OpenRouter works. To bypass OpenRouter entirely (e.g., direct Anthropic API), change `base_url` in `BaseAgent.__init__`.

---

## 11. Testing strategy

**Unit tests are fast and LLM-free.** They test the deterministic parts of the system:

```python
# test_resolver.py — does 2+2=4?
def test_market_clearing_shortage():
    """When demand > supply, price should increase."""
    supply = [Offer(volume=100, price=50)]
    demand = [Request(volume=150)]
    result = MarketClearing.clear(supply, demand)
    assert result.realized_price > 50
    assert result.unmet_demand_pct > 0

# test_capture.py — does lobbying accumulate correctly?
def test_capture_tipping_point():
    """Regulator flips to captured when lobbying exceeds threshold."""
    engine = CaptureEngine(make_test_world())
    engine.accumulate_lobbying("reg_dgtr", "tata_steel", amount=60)
    assert engine.get_state("reg_dgtr").is_captured == True

# test_visibility.py — does information filter correctly?
def test_company_cannot_see_private_signals():
    """Company should never see another agent's private intent."""
    signals = [AgentSignal(public="we are exploring", private="FDI committed")]
    filtered = VisibilityFilter.filter_for_agent(company_agent, signals, world)
    assert all(s.private is None for s in filtered)

# test_parser.py — does response parsing handle edge cases?
def test_parser_handles_markdown_fences():
    """LLM sometimes wraps JSON in ```json ... ```. Parser should strip."""
    raw = '```json\n{"agent_id": "test", "round": 1}\n```'
    result = ResponseParser._extract_json(raw)
    assert json.loads(result)["agent_id"] == "test"
```

**Integration tests use saved LLM responses.** Record one real run's LLM outputs as fixtures, then replay them to test the full pipeline without API calls.

**Smoke test** — one quick end-to-end run with 2 agents and 2 rounds using the cheapest model. Run this before every demo to catch environment issues.
