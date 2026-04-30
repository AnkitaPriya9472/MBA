# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Setup & Running

```bash
# Create and activate virtual environment
uv venv && source .venv/bin/activate

# Install dependencies
uv pip install -r requirements.txt

# Required env var — uses OpenRouter, not Anthropic directly
export OPENROUTER_API_KEY="your-key-here"
```

**Run via notebook (primary demo path):**
```bash
jupyter notebook notebooks/01_tariff_shock_demo.ipynb
```

**Run via terminal:**
```python
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
```

## Architecture

**LLM backend:** `agents/base.py` uses the OpenAI SDK pointed at OpenRouter (`https://openrouter.ai/api/v1`) with `OPENROUTER_API_KEY`. Both `BaseAgent` and `run_scenario()` default to `moonshotai/kimi-k2`. Pass a different `model` string to either to switch.

**Simulation loop** (`simulation/engine.py`):
- `ShockScenario` (loaded from `scenarios/*.json`) defines the external shock event
- `SimulationEngine.run()` iterates N rounds; each round, every agent sees the shock + all other agents' prior-round decisions, then calls the LLM to produce a `RoundResponse` (decision, reasoning, confidence, impact_areas, metrics_change)
- Agents maintain their own `memory: list[RoundResponse]` across rounds so decisions evolve
- `run_scenario()` is the convenience entrypoint

**Agent profiles** (`agents/profiles/*.json`) are real-world-grounded JSON files loaded into `AgentProfile`. Structure:
```json
{
  "name": "...", "role": "company|government|consumer|supplier|regulator",
  "description": "...", "objectives": [...], "constraints": [...],
  "data": { /* financials, market share, policy tools, etc. */ }
}
```

**Results** are `SimulationResult` objects with `.save(path)` for JSON persistence and `.get_round(n)` / `.get_agent_history(name)` helpers.

## Extending

- **New agent:** Add a JSON profile to `agents/profiles/` and pass its path to `run_scenario()`.
- **New scenario:** Add a JSON file to `scenarios/` with keys: `name`, `description`, `category`, `severity`, `affected_sectors`, `context`.
- **New model:** Pass `model=` to `run_scenario()` or directly to `BaseAgent(model=...)`. Any OpenRouter model slug works.
