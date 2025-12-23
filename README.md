# Sentinel: A Unified Cross-Commodity Signal Dashboard

Sentinel is a unified dashboard for cross-commodity trading signals.  
It brings together macroeconomic, fundamental, sentiment, and technical signals into a single, interpretable view to help traders understand **what is driving markets and why**.

The goal is not automated trading, but **decision support** through clear, explainable signals.

---

## What this project does
- Aggregates different types of trading signals in one place
- Standardizes how signals are represented (direction, confidence, explanation)
- Displays signals by market and category
- Enables cross-commodity comparison

---

## Signal Categories
Each signal belongs to one of four categories:

- **Macro** – Broad economic forces (USD, rates, growth)
- **Fundamental** – Supply/demand drivers (e.g. energy inventories)
- **Sentiment** – News flow and positioning
- **Technical** – Price-based indicators (trend, momentum)

Each signal answers:
- What market?
- What category?
- Bullish / Bearish / Neutral?
- How confident?
- Why?

---

## Scope
- Initial universe: limited set of commodities (e.g. energy, metals, ags)
- Update frequency: daily / weekly
- Output: signal table and per-market drill-down
- No live trading or execution

---

## Tech Stack (early-stage)
- **Python backend** (FastAPI)
- API-first design
- Data sources and pipelines will be added incrementally
- Cloud, Databricks, and Snowflake planned for later stages

---

## Repo Structure
