# Multi-Agent AI Simulation for Strategic Foresight

**Modelling Business Ecosystem Responses to External Shocks in the Indian Manufacturing Sector**

---

## The Thinking Behind This

Traditional strategic planning treats businesses as isolated entities — you analyse *your* company, *your* competitors, *your* market. But real economies are ecosystems. When the US slaps a tariff on Indian steel, it doesn't just hit Tata Steel. It cascades — the government retaliates, consumers scramble for alternatives, suppliers recalibrate pricing, and the ripple effects reshape the entire landscape within weeks.

The problem with conventional tools (SWOT, scenario planning, war-gaming) is that they're **static and single-actor**. You model what *you* would do, maybe what one competitor would do, but you can't easily simulate the **multi-actor feedback loops** that define real economic systems. A government response changes the supplier calculus, which changes the consumer's options, which changes the company's strategy — and the cycle repeats.

This project asks: **what if we could simulate that entire ecosystem?**

We use LLM-powered AI agents — each representing a real actor in the business ecosystem (companies, governments, consumers, suppliers, regulators) — grounded in **real financial data** from listed Indian companies. Each agent has its own objectives, constraints, and decision-making logic. When an external shock hits, they don't just react to the shock — they react to *each other*, over multiple rounds, producing emergent strategic dynamics that mirror how real ecosystems behave.

The result is a **strategic foresight tool**: inject a shock, watch the ecosystem respond, and extract pre-emptive insights before the shock ever happens in the real world.

### Why This Matters

- **For companies**: Test how your ecosystem will react to disruptions before they happen. Identify second-order effects you'd miss in a static analysis.
- **For regulators**: Simulate policy interventions and see how the market actually responds — including workarounds, unintended consequences, and feedback loops.
- **For strategists**: Move from "what should *we* do?" to "what will the *system* do?" — a fundamentally different question that produces fundamentally better answers.

### Academic Grounding

This isn't just an engineering exercise. The simulation is grounded in established theoretical frameworks:

| Framework | How It's Applied |
|---|---|
| **PESTLE Analysis** | Mapping external shock categories to macro dimensions |
| **Porter's Five Forces** | Structuring competitive dynamics within the simulated ecosystem |
| **Game Theory (Prisoner's Dilemma)** | Modelling cartel/collusion scenarios between competing agents |
| **Principal-Agent Theory** | Modelling corporate fraud and information asymmetry |
| **Antitrust Economics** | Modelling regulator responses to collusion and market concentration |

---

## Project Structure

```
mba/
├── agents/                     # Agent definitions and profiles
│   ├── base.py                 # BaseAgent class — the core building block
│   └── profiles/               # JSON files with real-world data for each agent
│       ├── tata_steel.json
│       ├── indian_government.json
│       ├── steel_consumer.json
│       └── iron_ore_supplier.json
│
├── simulation/                 # Simulation engine
│   └── engine.py               # Orchestrates multi-round agent interactions
│
├── scenarios/                  # External shock definitions
│   └── tariff_shock.json       # First scenario: US steel tariff escalation
│
├── notebooks/                  # Jupyter notebooks for running and presenting
│   └── 01_tariff_shock_demo.ipynb
│
├── data/                       # Simulation results (generated after runs)
│
└── requirements.txt            # Python dependencies
```

### What Each Directory Does

**`agents/`** — This is where ecosystem actors live. `base.py` defines the `BaseAgent` class: an LLM-powered agent that takes a role, a data profile, and a system prompt, then generates strategic decisions via the Claude API. Each agent maintains memory across simulation rounds so its decisions evolve as it sees what other agents do. The `profiles/` subfolder holds JSON files containing real-world data (financials, market position, policy tools) that ground each agent's reasoning in reality.

**`simulation/`** — The orchestration layer. `engine.py` contains the `SimulationEngine` that loads a shock scenario, initialises agents, and runs N rounds of interaction. Each round, every agent sees the shock plus all other agents' previous decisions, then responds. The engine collects structured results (decision, reasoning, confidence, metrics) and displays them using rich terminal formatting.

**`scenarios/`** — External shock definitions as JSON files. Each scenario specifies a shock event (what happened), its category and severity, affected sectors, and background context. This is what gets injected into the simulation to trigger agent responses.

**`notebooks/`** — Jupyter notebooks that tie everything together for presentation. Each notebook loads a scenario, runs the simulation, and analyses the results with tables and data summaries. These produce the outputs that go directly into the project report.

**`data/`** — Where simulation results are saved as JSON after each run. These can be reloaded for further analysis or comparison across scenarios.

---

## How to Run

### Prerequisites

- Python 3.11+
- A Claude API key from [Anthropic](https://console.anthropic.com/)

### Setup

```bash
# Create and activate virtual environment
uv venv && source .venv/bin/activate

# Install dependencies
uv pip install -r requirements.txt

# Set your API key
export ANTHROPIC_API_KEY="your-key-here"
```

### Run via Jupyter Notebook (recommended)

```bash
jupyter notebook notebooks/01_tariff_shock_demo.ipynb
```

Run all cells. The simulation takes ~1-2 minutes (4 agents x 3 rounds of Claude API calls). You'll see each agent's decisions rendered in real-time, followed by a summary table and analysis.

### Run via Terminal

```bash
python -c "
from simulation.engine import run_scenario
result = run_scenario(
    'scenarios/tariff_shock.json',
    [
        'agents/profiles/tata_steel.json',
        'agents/profiles/indian_government.json',
        'agents/profiles/steel_consumer.json',
        'agents/profiles/iron_ore_supplier.json',
    ],
    rounds=3,
)
result.save('data/tariff_shock_results.json')
"
```

---

## How to Extend

### Add a New Agent

1. Create a JSON profile in `agents/profiles/`. Follow the structure of existing profiles:
   ```json
   {
     "name": "Agent Display Name",
     "role": "company | government | consumer | supplier | regulator",
     "description": "Who this agent is and what it does",
     "objectives": ["What it's trying to achieve"],
     "constraints": ["What limits its actions"],
     "data": { "real_world_data": "grounded in annual reports or public sources" }
   }
   ```
2. Add the profile path to your notebook or run command.

### Add a New Shock Scenario

1. Create a JSON file in `scenarios/`:
   ```json
   {
     "name": "Shock headline",
     "description": "What happened — detailed enough for agents to reason about",
     "category": "tariff | geopolitical | regulatory | market_entry | fraud | macro",
     "severity": "low | medium | high | extreme",
     "affected_sectors": ["List of affected sectors"],
     "context": "Background information and wider implications"
   }
   ```
2. Create a new notebook in `notebooks/` or modify the scenario path in an existing one.

### Add a New Company Ecosystem

To simulate a different company (e.g., Maruti Suzuki facing EV disruption):

1. Create company agent profile with real data from annual reports
2. Create relevant ecosystem agent profiles (regulator, competitor, consumer, supplier)
3. Create a shock scenario relevant to that ecosystem
4. Create a notebook that wires them together

### Adjust Simulation Parameters

- **Rounds**: Change the `rounds` parameter (default: 3). More rounds = more interaction but higher API cost.
- **Model**: Change the model in `BaseAgent` constructor. Use `claude-sonnet-4-6` for speed/cost, `claude-opus-4-6` for deeper reasoning.

---

## Scenarios Roadmap

| Scenario | Status | Agents |
|---|---|---|
| US Steel Tariff Escalation | Done | Tata Steel, Govt, Consumer, Supplier |
| EV Market Disruption (Maruti) | Planned | Maruti Suzuki, EV Entrant, Govt, Consumer |
| Raw Material Price Spike | Planned | Tata Steel, Supplier, Govt, Consumer |
| Corporate Fraud Event | Planned | Company, Regulator, Investor, Media |
| Cartel/Prisoner's Dilemma | Planned | Steel Co. A, Steel Co. B, Regulator |
| Demonetisation-type Macro Shock | Planned | Multiple companies, Govt, Consumer, Banks |
