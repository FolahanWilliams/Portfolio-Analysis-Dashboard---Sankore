"""Grounded AI assistant for the portfolio dashboard.

Design goal: accuracy above all. The model does NO arithmetic and invents NO
numbers. We hand it the exact figures our own (audited) analytics produce --
pre-formatted into the units they'll be spoken in (percent as %, money in USD)
-- and instruct it to answer only from that context. Common superlatives
("biggest position", "worst performer", "most concentrated sector") are
pre-computed so the model just reads the answer.

Transport is stdlib urllib to the Gemini API (no extra runtime dependency,
consistent with app/data/live.py). Model + key come from the environment:
    GEMINI_API_KEY   required
    GEMINI_MODEL     default "gemini-3.1-flash-lite"
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

from app.data.loader import MarketData, load_market_data
from app.analytics.windows import resolve_window
from app.analytics.summary import compute_summary
from app.analytics.holdings import compute_holdings
from app.analytics.exposure import compute_exposure
from app.analytics.risk import compute_risk
from app.analytics.attribution import compute_attribution
from app.analytics.alerts import compute_alerts

_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
_DEFAULT_MODEL = "gemini-3.1-flash-lite"


# ---- formatting helpers: everything the model sees is already in its final unit
def _pct(x, dp=2):
    if x is None:
        return None
    return f"{x*100:+.{dp}f}%"


def _pctu(x, dp=1):  # unsigned percent (weights)
    if x is None:
        return None
    return f"{x*100:.{dp}f}%"


def _money(x):
    if x is None:
        return None
    return f"-${abs(x):,.0f}" if x < 0 else f"${x:,.0f}"


def _price(x):
    if x is None:
        return None
    return f"-${abs(x):,.2f}" if x < 0 else f"${x:,.2f}"


def _num(x, dp):
    return round(float(x), dp) if x is not None else None


def build_context(md: MarketData) -> dict:
    """Assemble the compact, pre-formatted, single-source-of-truth data pack."""
    w = resolve_window("ALL", md.dates)
    summ = compute_summary(md, w)
    hold = compute_holdings(md)
    exp = compute_exposure(md, w)
    risk = compute_risk(md, w)
    attr = compute_attribution(md, w)
    alerts = compute_alerts(md, w)

    H = hold["holdings"]
    holdings = [{
        "ticker": h["ticker"], "name": h["name"], "sector": h["sector"], "region": h["region"],
        "units": round(h["shares"]),
        "purchase_price": _price(h["cost_price"]),
        "current_price": _price(h["current_price"]),
        "cost_basis": _money(h["cost_value"]),
        "market_value": _money(h["market_value"]),
        "gain_dollars": _money(h["unrealised_pnl"]),
        "gain_pct": _pct(h["unrealised_return"]),
        "weight_of_equity": _pctu(h["weight"]),
    } for h in H]

    # Pre-computed superlatives so the model never has to sort/compare.
    by_gain = sorted(H, key=lambda h: h["unrealised_return"])
    by_dollars = sorted(H, key=lambda h: h["unrealised_pnl"])
    by_weight = sorted(H, key=lambda h: h["weight"], reverse=True)
    key_facts = {
        "largest_position": f'{by_weight[0]["ticker"]} at {_pctu(by_weight[0]["weight"])} of equity',
        "top_5_positions": ", ".join(f'{h["ticker"]} {_pctu(h["weight"])}' for h in by_weight[:5]),
        "best_performer_pct": f'{by_gain[-1]["ticker"]} {_pct(by_gain[-1]["unrealised_return"])}',
        "worst_performer_pct": f'{by_gain[0]["ticker"]} {_pct(by_gain[0]["unrealised_return"])}',
        "biggest_dollar_gain": f'{by_dollars[-1]["ticker"]} {_money(by_dollars[-1]["unrealised_pnl"])}',
        "biggest_dollar_loss": f'{by_dollars[0]["ticker"]} {_money(by_dollars[0]["unrealised_pnl"])}',
        "positions_at_a_loss": f'{summ["positions_at_loss"]} of {summ["holdings_count"]}',
    }

    return {
        "as_of": summ["as_of"],
        "inception": risk["inception"],
        "benchmark": "S&P 500",
        "base_currency": "USD",
        "data_provenance": (
            "Cost basis and share counts are fixed from the holdings sheet. Current prices are "
            "live from Yahoo Finance, so market value and gains reflect the live market. The S&P 500 "
            "benchmark price history starts at the same inception as the holdings."
        ),
        "portfolio_summary": {
            "market_value_aum": _money(summ["aum"]),
            "cost_basis": _money(summ["cost_basis"]),
            "unrealised_pnl": _money(summ["pnl"]["unrealised"]),
            "return_since_purchase": _pct(summ["total_return"]),
            "return_basis": "cost-based book P&L = (market value - cost basis) / cost basis",
            "positions_at_a_loss": key_facts["positions_at_a_loss"],
            "holdings_count": summ["holdings_count"],
        },
        "performance_vs_sp500_inception_to_date": {
            "note": ("Measures the CURRENT holdings across the full price history since inception vs the "
                     "S&P 500 -- the like-for-like basis for risk. Distinct from 'return_since_purchase' above."),
            "portfolio_return": _pct(risk["portfolio_return"]),
            "sp500_return": _pct(risk["benchmark_return"]),
            "excess_above_market": _pct(risk["excess_return"]),
            "beta": _num(risk["beta"], 2),
            "alpha_annualised_capm": _pct(risk["alpha"]),
            "volatility_annualised": _pctu(risk["volatility"]),
            "sp500_volatility_annualised": _pctu(risk["benchmark_volatility"]),
            "sharpe": _num(risk["sharpe"], 2),
            "max_drawdown": _pctu(risk["max_drawdown"]),
            "value_at_risk_1day_99pct": _pctu(risk["var"]["99"]["historical"], 2),
            "risk_free_rate": _pctu(risk["risk_free_rate"]),
        },
        "key_facts": key_facts,
        "holdings": holdings,
        "sector_weights": {r["sector"]: _pctu(r["portfolio"]) for r in exp["sector"]},
        "region_weights": {r["region"]: _pctu(r["portfolio"]) for r in exp["region"]},
        "concentration": {
            "effective_holdings": _num(exp["concentration"]["effective_n"], 1),
            "largest_weight": _pctu(exp["concentration"]["largest_weight"]),
            "top5_weight": _pctu(exp["concentration"]["top5_weight"]),
            "hhi": _num(exp["concentration"]["hhi"], 3),
        },
        "sector_contribution_to_return": {
            s["sector"]: _pct(s["contribution"]) for s in attr["sector_contribution"]
        },
        "risk_alerts": [
            {"severity": a["severity"], "title": a["title"], "detail": a["detail"]}
            for a in alerts["alerts"]
        ],
    }


SYSTEM_PROMPT = """You are the portfolio analyst assistant for the Sankore GEF portfolio dashboard, \
speaking to a professional investment team.

You are given a DATA block that is the SINGLE SOURCE OF TRUTH. Every number in it has been \
computed and independently audited by the dashboard's analytics engine and is already formatted \
in its final unit (percentages as %, money in USD).

Rules:
- Answer ONLY from the DATA. Quote figures exactly as written. NEVER recompute, estimate, round \
differently, or invent a number. If a figure isn't in the DATA, say you don't have that data.
- Keep two returns distinct: "return since purchase" is the cost-based book P&L; the \
"performance vs S&P 500 inception-to-date" block is the time-series comparison used for beta/alpha/vol.
- For "why" / driver questions, cite the specific holdings, sectors, or alerts in the DATA.
- Tone: accurate first, then thorough and concise. Lead with the direct answer, then the supporting \
figures. Use tight bullets or short sentences. No preamble, no hedging, no "as an AI" disclaimers, \
no advice to consult a professional.
- If asked something outside the portfolio's data (e.g. live news, forecasts), say it's outside \
the dashboard data."""


def _configured() -> tuple[str | None, str]:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    model = os.environ.get("GEMINI_MODEL", _DEFAULT_MODEL).strip() or _DEFAULT_MODEL
    return (key or None), model


def _call_gemini(key: str, model: str, system: str, contents: list[dict]) -> str:
    body = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": contents,
        "generationConfig": {"temperature": 0.0, "topP": 0.1, "maxOutputTokens": 1200},
    }
    url = _ENDPOINT.format(model=model) + "?key=" + urllib.parse.quote(key)
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        payload = json.loads(resp.read())
    cands = payload.get("candidates") or []
    if not cands:
        fb = payload.get("promptFeedback", {})
        raise RuntimeError(f"No answer returned (feedback: {fb}).")
    parts = cands[0].get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts).strip()
    return text or "I couldn't produce an answer from the data."


def answer(question: str, history: list[dict] | None = None) -> dict:
    """Answer a question grounded in the current portfolio data."""
    key, model = _configured()
    md = load_market_data()
    ctx = build_context(md)
    grounded_as_of = ctx["as_of"]

    if not key:
        return {
            "answer": ("The AI assistant isn't configured yet. Add a GEMINI_API_KEY environment "
                       "variable in Vercel (and optionally GEMINI_MODEL) to enable it."),
            "configured": False,
            "model": model,
            "grounded_as_of": grounded_as_of,
        }

    system = SYSTEM_PROMPT + "\n\nDATA (single source of truth):\n" + json.dumps(ctx, indent=1)
    contents: list[dict] = []
    for m in (history or [])[-8:]:
        role = "model" if m.get("role") == "model" else "user"
        txt = str(m.get("text", ""))[:2000]
        if txt:
            contents.append({"role": role, "parts": [{"text": txt}]})
    contents.append({"role": "user", "parts": [{"text": question[:2000]}]})

    try:
        text = _call_gemini(key, model, system, contents)
        return {"answer": text, "configured": True, "model": model, "grounded_as_of": grounded_as_of}
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "ignore")[:300]
        return {
            "answer": (f"The AI service returned an error ({e.code}). If the model name is wrong, set "
                       f"GEMINI_MODEL in Vercel. Detail: {detail}"),
            "configured": True, "model": model, "grounded_as_of": grounded_as_of, "error": True,
        }
    except Exception as e:  # pragma: no cover - network/runtime guard
        return {
            "answer": f"The AI assistant hit an error reaching the model: {str(e)[:200]}",
            "configured": True, "model": model, "grounded_as_of": grounded_as_of, "error": True,
        }
