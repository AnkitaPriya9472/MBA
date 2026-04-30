# The Idea

> This document captures the evolving vision behind this project. It is a living file — update it as the idea grows.

---

## The Problem with Traditional Strategy

Traditional strategic planning treats businesses as isolated entities. You analyse *your* company, *your* competitors, *your* market. Tools like SWOT, Porter's Five Forces, and scenario planning are powerful — but they are fundamentally **static and single-actor**.

When the US slaps a tariff on Indian steel, it doesn't just hit Tata Steel. It cascades:
- The government retaliates with policy measures
- Consumers scramble for substitutes or absorb costs
- Suppliers recalibrate pricing and availability
- Competitors adjust market positioning

These are **multi-actor feedback loops** playing out in real time. Conventional tools can't simulate them. You model what *you* would do, maybe one competitor — but the ecosystem is reacting to itself, not just to the shock.

---

## The Core Idea

**What if we could simulate the entire ecosystem?**

A set of LLM-powered AI agents — each representing a real actor (company, government, consumer, supplier, regulator) — grounded in **real financial data** from listed Indian companies. Each agent has its own objectives, constraints, and decision-making logic.

When an external shock hits, they don't just react to the shock. They react to **each other**, over multiple rounds, producing emergent strategic dynamics that mirror how real ecosystems behave.

The output: a **strategic foresight tool**. Inject a shock, watch the ecosystem respond, extract pre-emptive insights before the shock ever reaches the real world.

---

## What Makes This Different

- **Multi-actor, not single-actor** — the ecosystem responds as a system, not as individual players
- **Dynamic, not static** — agent decisions evolve across rounds as they observe each other
- **Grounded in real data** — agent profiles built from annual reports, balance sheets, and exchange filings of listed Indian companies (Tata Steel, Maruti Suzuki)
- **Theoretically anchored** — not a toy; rooted in PESTLE, Porter's Five Forces, Game Theory, Principal-Agent Theory, Antitrust Economics

---

## Who It's For

| Audience | Value |
|---|---|
| **Companies** | Test how your ecosystem reacts to disruptions before they happen. Identify second-order effects you'd miss in a static analysis. |
| **Regulators** | Simulate policy interventions and observe how the market responds — including workarounds and unintended consequences. |
| **Strategists** | Move from "what should *we* do?" to "what will the *system* do?" — a fundamentally different question. |

---

## The Shocks We Model

The simulation is shock-agnostic by design. Current and planned scenarios:

- **Trade & tariffs** — e.g., US steel tariff escalation (active)
- **EV disruption** — new market entrant forcing ecosystem restructuring (planned)
- **Raw material price spike** — supply-side shock propagation (planned)
- **Corporate fraud** — information asymmetry, regulator response, investor panic (planned)
- **Cartel formation** — Prisoner's Dilemma dynamics between competing agents (planned)
- **Macro shocks** — demonetisation-type events with broad ecosystem effects (planned)

---

## The Horizon

This started as an MBA project. The ambition is bigger.

| Horizon | What it looks like |
|---|---|
| **H1 — Now** | MBA prototype: real data, LLM agents, notebook demo, academic submission |
| **H2 — Next** | Web-based war-game tool: configurable agents, drag-and-drop shocks, exportable insights |
| **H3 — Future** | SaaS product for risk analysts and strategy consultants: real-time data feeds, broader agent types, scenario libraries |

---

## Open Questions (as of now)

- How do we validate simulation outputs against historical events? (back-testing)
- What's the right number of rounds before agent responses converge?
- Can agent profiles be auto-generated from public filings (annual reports → structured JSON)?
- How do we handle shock interactions — e.g., a tariff shock coinciding with a raw material spike?
- At H2, how do we make the ecosystem configurable without requiring code changes?
