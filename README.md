# Portfolio Intelligence Dashboard

An internal web app that ingests a fund's **holdings, prices, and benchmark** and
shows, on one screen, **what the portfolio holds, how much risk it carries, and
what drove performance** — replacing the manual spreadsheet assembly of those
views.

This is a 3-week prototype on mock data, built as a **production-track
foundation**: the analytics layer is fully separated from presentation so it can
graduate to formal use without a rewrite.

![Dashboard](docs/dashboard-screenshot.png)

---

## Architecture

```
 Mock CSVs            FastAPI + pandas/numpy              React + Vite + TS
 holdings ─┐          ┌───────────────────────┐          ┌──────────────────┐
 prices   ─┼─ load ─▶ │ validate → FX→USD →    │ ─JSON──▶ │ shell + 4 sections│
 benchmark ┤  & flag  │ compute metrics → serve│   REST   │ charts & tables   │
 fx       ─┘          └───────────────────────┘          └──────────────────┘
        (the only layer        all fund math lives        renders only — holds
         touching raw data)    here · validated ±0.1%     no fund math
```

**The frontend never computes fund math. The backend never handles
presentation.** Every cross-holding total is normalised to USD before
aggregation; malformed rows are skipped and flagged, never crash the app.

- **Backend** — Python · FastAPI · pandas/numpy. Four thin REST endpoints
  (`/summary`, `/exposure`, `/risk`, `/attribution`) plus `/meta` and `/health`.
- **Frontend** — React · TypeScript · Vite · Tailwind · Recharts. A single-screen
  dashboard with a global window selector (MTD/QTD/YTD/1Y/All).

See [`docs/workflow-map.md`](docs/workflow-map.md) for the foundation workflow map.

---

## Repository layout

```
backend/
  app/
    config.py             constants (base ccy, risk-free, trading days)
    data/loader.py        load + validate + USD-normalise (the data-swap point)
    analytics/            presentation-free fund math
      windows.py          MTD/QTD/YTD/1Y/ALL resolution
      summary.py          AUM, P&L, returns, contributors
      exposure.py         weights, active weights, HHI, heatmap
      risk.py             vol, beta, Sharpe, VaR, correlation, drawdown
      attribution.py      period returns, contribution, Brinson
    models/schemas.py     window enum
    main.py               FastAPI app + endpoints
    mock_data/            generated CSVs
  scripts/generate_mock_data.py
  tests/test_analytics.py validation vs independent reference
frontend/
  src/
    api/client.ts         typed fetch client
    types/api.ts          TS mirror of the JSON contract
    lib/                  formatting + fetch hook
    components/           shell, cards, matrix, ui states
    sections/             the four P0 sections
    App.tsx
docs/
```

---

## Running it

Prerequisites: Python 3.11+, Node 20+.

```bash
# 1. Backend  (http://localhost:8000)
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/generate_mock_data.py      # writes app/mock_data/*.csv
uvicorn app.main:app --reload

# 2. Frontend (http://localhost:5173) — in a second terminal
cd frontend
npm install
npm run dev
```

The Vite dev server proxies `/api` → `http://localhost:8000`, so the app works
with no CORS setup. Open http://localhost:5173.

Or use the shortcuts:

```bash
make setup     # install backend + frontend deps, generate data
make backend   # run the API
make frontend  # run the dev server
make test      # backend validation tests
```

---

## Data (mock)

A deterministic, seeded generator produces ~7.5 months of daily history
(Nov 2025 → Jun 2026) for an S&P-tech-style universe. A few non-USD listings
(ASML, SAP in EUR; Tencent in HKD) exercise the currency-normalisation path.
Prices use a single-factor model (market factor + idiosyncratic noise) so betas
and correlations are realistic. The seed is chosen so the demo shows a healthy
up-period (~+19%) with a realistic correction.

To swap in real data later, replace the four CSVs (or point the loader at a live
feed) — **nothing in the analytics or frontend changes.**

---

## Validation

`backend/tests/test_analytics.py` recomputes key metrics with an independent
numpy/pandas path and asserts they match within ±0.1%, plus checks the Brinson
reconciliation identity (allocation + selection + interaction = active return).

```bash
cd backend && source .venv/bin/activate && pytest -q
```

---

## Scope

- **P0 (shipped in this draft):** Portfolio Summary, Sector & Geographic
  Exposure, Risk Metrics, Performance Attribution.
- **P1 (next):** rule-based alert feed, scenario shocks, one-click PDF report.
- **Out of scope (production phase):** live custodian/brokerage feeds, trading,
  multi-user auth/persistence, intraday streaming.

## Notes / decisions

- **Frontend = React + Vite** (not Next.js): a single-screen dashboard with all
  computation in FastAPI doesn't need SSR/routing; a Vite SPA keeps the
  frontend/backend split clean and the initial load fast.
- VaR is reported as a positive 1-day loss fraction, both historical and
  parametric. 1Y on the mock set is flagged as truncated (history starts in Nov).
