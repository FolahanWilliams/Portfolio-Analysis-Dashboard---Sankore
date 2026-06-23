import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import type { Scenario, ScenarioHolding } from "../types/api";
import { Card, ErrorState, Loading, StatTile } from "../components/ui";
import { fmtMoney, fmtSignedPct, signClass } from "../lib/format";

const MARKET_STEPS = [-20, -10, -5, 0, 5, 10];
const FX = ["EUR", "HKD"];

type Pct = Record<string, number>;

function pctToFrac(p: Pct): Pct {
  return Object.fromEntries(Object.entries(p).map(([k, v]) => [k, v / 100]));
}

function MoverRow({ h }: { h: ScenarioHolding }) {
  return (
    <div className="flex items-center justify-between py-1 text-sm">
      <span className="font-medium text-slate-600">{h.ticker}</span>
      <span className="flex items-center gap-3">
        <span className={`tabular ${signClass(h.shock_return)}`}>{fmtSignedPct(h.shock_return)}</span>
        <span className={`w-20 text-right tabular ${signClass(h.value_change)}`}>
          {fmtMoney(h.value_change)}
        </span>
      </span>
    </div>
  );
}

export function ScenarioSection({ sectors }: { sectors: string[] }) {
  const [market, setMarket] = useState(0);
  const [sectorShocks, setSectorShocks] = useState<Pct>({});
  const [fxShocks, setFxShocks] = useState<Pct>({});
  const [data, setData] = useState<Scenario | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const reqKey = useMemo(
    () => JSON.stringify({ market, sectorShocks, fxShocks }),
    [market, sectorShocks, fxShocks],
  );

  useEffect(() => {
    let alive = true;
    setLoading(true);
    api
      .scenario({
        market: market / 100,
        sector_shocks: pctToFrac(sectorShocks),
        fx_shocks: pctToFrac(fxShocks),
      })
      .then((d) => alive && (setData(d), setError(null)))
      .catch((e) => alive && setError(e.message))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reqKey]);

  const reset = () => {
    setMarket(0);
    setSectorShocks({});
    setFxShocks({});
  };
  const preset = (m: number, s: Pct = {}, f: Pct = {}) => {
    setMarket(m);
    setSectorShocks(s);
    setFxShocks(f);
  };

  return (
    <Card
      title="Scenario Analysis"
      subtitle="Shock the book and reprice it instantly"
      right={
        <div className="flex flex-wrap gap-1.5">
          <PresetBtn onClick={() => preset(-10)}>Risk-off −10%</PresetBtn>
          <PresetBtn onClick={() => preset(-5, { Semiconductors: -12 })}>Tech selloff</PresetBtn>
          <PresetBtn onClick={() => preset(0, {}, { EUR: -5, HKD: -5 })}>USD strength</PresetBtn>
          <PresetBtn onClick={reset}>Reset</PresetBtn>
        </div>
      }
    >
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Controls */}
        <div>
          <h3 className="mb-2 text-xs font-semibold text-slate-500">Market shock</h3>
          <div className="flex flex-wrap gap-1.5">
            {MARKET_STEPS.map((m) => (
              <button
                key={m}
                onClick={() => setMarket(m)}
                className={`rounded-md px-3 py-1.5 text-sm font-medium tabular transition ${
                  market === m
                    ? "bg-navy text-white"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                }`}
              >
                {m > 0 ? `+${m}` : m}%
              </button>
            ))}
          </div>
          <p className="mt-1 text-[11px] text-slate-400">Applied to each holding via its beta.</p>

          <h3 className="mb-2 mt-5 text-xs font-semibold text-slate-500">Sector shocks (%)</h3>
          <div className="grid grid-cols-2 gap-2">
            {sectors.map((s) => (
              <label key={s} className="flex items-center justify-between gap-2 text-sm">
                <span className="truncate text-slate-600">{s}</span>
                <input
                  type="number"
                  value={sectorShocks[s] ?? 0}
                  onChange={(e) =>
                    setSectorShocks((p) => ({ ...p, [s]: Number(e.target.value) }))
                  }
                  className="w-16 rounded border border-slate-200 px-2 py-1 text-right tabular"
                />
              </label>
            ))}
          </div>

          <h3 className="mb-2 mt-5 text-xs font-semibold text-slate-500">FX shocks vs USD (%)</h3>
          <div className="flex gap-3">
            {FX.map((c) => (
              <label key={c} className="flex items-center gap-2 text-sm">
                <span className="text-slate-600">{c}</span>
                <input
                  type="number"
                  value={fxShocks[c] ?? 0}
                  onChange={(e) => setFxShocks((p) => ({ ...p, [c]: Number(e.target.value) }))}
                  className="w-16 rounded border border-slate-200 px-2 py-1 text-right tabular"
                />
              </label>
            ))}
          </div>
        </div>

        {/* Results */}
        <div>
          {error && <ErrorState message={error} />}
          {loading && !data && <Loading label="Repricing" />}
          {!error && data && (
            <>
              <div className="grid grid-cols-2 gap-3">
                <StatTile
                  label="Repriced AUM"
                  value={fmtMoney(data.new_aum)}
                  sub={<span className="text-slate-400">from {fmtMoney(data.base_aum)}</span>}
                  tone="value"
                />
                <StatTile
                  label="P&L impact"
                  value={<span className={signClass(data.pnl_change)}>{fmtMoney(data.pnl_change)}</span>}
                  sub={
                    <span className={signClass(data.portfolio_return)}>
                      {fmtSignedPct(data.portfolio_return)}
                    </span>
                  }
                />
              </div>
              <div className="mt-4 grid grid-cols-2 gap-6">
                <div>
                  <h4 className="mb-1 text-xs font-semibold text-positive">Top gainers</h4>
                  {data.top_gainers.map((h) => <MoverRow key={h.ticker} h={h} />)}
                </div>
                <div>
                  <h4 className="mb-1 text-xs font-semibold text-negative">Top losers</h4>
                  {data.top_losers.map((h) => <MoverRow key={h.ticker} h={h} />)}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </Card>
  );
}

function PresetBtn({ children, onClick }: { children: React.ReactNode; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="rounded-md bg-blue-50 px-2.5 py-1 text-xs font-medium text-brand hover:bg-blue-100"
    >
      {children}
    </button>
  );
}
