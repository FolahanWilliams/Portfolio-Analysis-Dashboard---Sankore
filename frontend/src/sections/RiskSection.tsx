import { api } from "../api/client";
import { useApi } from "../lib/useApi";
import type { Risk, SnapshotRisk, WindowCode } from "../types/api";
import { Card, EmptyState, ErrorState, Loading, Pill, StatTile, TruncatedNote } from "../components/ui";
import { fmtMoney, fmtNum, fmtPct, fmtSignedPct, signClass } from "../lib/format";

function SnapshotRiskView({ data }: { data: SnapshotRisk }) {
  return (
    <Card
      title="Concentration & Risk"
      subtitle={`As of ${data.as_of} · positioning risk from the snapshot`}
      right={<Pill tone="blue">snapshot</Pill>}
    >
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatTile label="Effective N" value={fmtNum(data.effective_n, 1)} tone="value" />
        <StatTile label="HHI" value={fmtNum(data.hhi, 3)} />
        <StatTile label="Top-5 weight" value={fmtPct(data.top5_weight, 1)} />
        <StatTile
          label="Positions at a loss"
          value={`${data.positions_at_loss} / ${data.positions}`}
        />
      </div>
      <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatTile
          label={`Largest — ${data.largest_weight.ticker}`}
          value={fmtPct(data.largest_weight.weight, 1)}
        />
        <StatTile
          label={`Top sector — ${data.largest_sector.sector}`}
          value={fmtPct(data.largest_sector.weight, 1)}
        />
        <StatTile label="Est. market beta" value={`${fmtNum(data.assumed_beta, 2)}×`} />
        <StatTile
          label={`Worst — ${data.worst.ticker}`}
          value={<span className="text-negative">{fmtSignedPct(data.worst.return)}</span>}
        />
      </div>

      <div className="mt-5">
        <h3 className="mb-2 text-xs font-semibold text-slate-500">Biggest drawdowns from cost</h3>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-[11px] uppercase tracking-wide text-slate-400">
              <th className="py-1 text-left font-medium">Holding</th>
              <th className="py-1 text-right font-medium">Below cost</th>
              <th className="py-1 text-right font-medium">P&L</th>
            </tr>
          </thead>
          <tbody>
            {data.loss_makers.map((l) => (
              <tr key={l.ticker} className="border-t border-slate-50">
                <td className="py-1.5 font-medium text-slate-700">{l.ticker}</td>
                <td className="py-1.5 text-right tabular text-negative">{fmtSignedPct(l.return)}</td>
                <td className="py-1.5 text-right tabular text-negative">{fmtMoney(l.value_change)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="mt-2 text-[11px] text-slate-400">
          Est. market beta uses assumed sector sensitivities (no price history to estimate it).
          Volatility, VaR, realised beta and correlation populate once a daily price history is captured.
        </p>
      </div>
    </Card>
  );
}

export function RiskSection({ window, live = false, refreshTick = 0 }: { window: WindowCode; live?: boolean; refreshTick?: number }) {
  const { data, loading, error } = useApi(() => api.risk(window, live), [window, live, refreshTick]);

  if (loading) return <Card title="Risk Metrics"><Loading /></Card>;
  if (error) return <Card title="Risk Metrics"><ErrorState message={error} /></Card>;
  if (!data) return <Card title="Risk Metrics"><EmptyState message="No data" /></Card>;

  if ((data as SnapshotRisk).mode === "snapshot") {
    return <SnapshotRiskView data={data as SnapshotRisk} />;
  }
  const d = data as Risk;
  const var95 = d.var["95"];
  const var99 = d.var["99"];

  return (
    <Card
      title="Performance & Risk vs S&P 500"
      subtitle={`Inception-to-date (${d.inception} → ${d.as_of}) · benchmark ${d.benchmark_name} · rf ${fmtPct(d.risk_free_rate, 1)}`}
      right={<TruncatedNote when={d.truncated} />}
    >
      {/* Headline: portfolio vs S&P 500 over the full price history */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <StatTile
          label="Portfolio return"
          value={<span className={signClass(d.portfolio_return)}>{fmtSignedPct(d.portfolio_return, 1)}</span>}
          tone="value"
        />
        <StatTile
          label={`${d.benchmark_name} return`}
          value={<span className={signClass(d.benchmark_return)}>{fmtSignedPct(d.benchmark_return, 1)}</span>}
        />
        <StatTile
          label="Excess (above market)"
          value={<span className={signClass(d.excess_return)}>{fmtSignedPct(d.excess_return, 1)}</span>}
        />
        <StatTile
          label="Alpha (ann., CAPM)"
          value={<span className={signClass(d.alpha)}>{fmtSignedPct(d.alpha, 1)}</span>}
        />
        <StatTile label="Beta" value={fmtNum(d.beta, 2)} />
        <StatTile
          label="Volatility (ann.)"
          value={fmtPct(d.volatility, 1)}
          sub={<span className="text-slate-400">S&P {fmtPct(d.benchmark_volatility, 1)}</span>}
        />
      </div>
      <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatTile
          label="Sharpe"
          value={<span className={signClass(d.sharpe)}>{fmtNum(d.sharpe, 2)}</span>}
        />
        <StatTile label="Max drawdown" value={<span className="text-negative">{fmtPct(d.max_drawdown, 1)}</span>} />
        <StatTile label="Observations" value={fmtNum(d.observations, 0)} />
        <StatTile label="Risk-free" value={fmtPct(d.risk_free_rate, 1)} />
      </div>
      <p className="mt-2 text-[11px] text-slate-400">
        Beta, alpha, volatility and the return comparison measure the <em>current</em> holdings across the full price
        history since {d.inception} vs the {d.benchmark_name} — the like-for-like basis for risk. This is distinct from the
        book’s gain since the positions were actually purchased (the “Return since purchase” in Portfolio Summary).
      </p>

      <div className="mt-5">
        <h3 className="mb-2 text-xs font-semibold text-slate-500">Value at Risk (1-day)</h3>
        <div className="overflow-hidden rounded-lg ring-1 ring-slate-100">
          <table className="w-full text-sm">
            <thead className="bg-slate-50/80">
              <tr className="text-[11px] uppercase tracking-wide text-slate-400">
                <th className="px-3 py-2 text-left font-medium">Confidence</th>
                <th className="px-3 py-2 text-right font-medium">Historical</th>
                <th className="px-3 py-2 text-right font-medium">Parametric</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-t border-slate-50">
                <td className="px-3 py-2 font-medium text-slate-700">95%</td>
                <td className="px-3 py-2 text-right tabular text-negative">{fmtPct(var95.historical, 2)}</td>
                <td className="px-3 py-2 text-right tabular text-negative">{fmtPct(var95.parametric, 2)}</td>
              </tr>
              <tr className="border-t border-slate-50">
                <td className="px-3 py-2 font-medium text-slate-700">99%</td>
                <td className="px-3 py-2 text-right tabular text-negative">{fmtPct(var99.historical, 2)}</td>
                <td className="px-3 py-2 text-right tabular text-negative">{fmtPct(var99.parametric, 2)}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p className="mt-2 text-[11px] text-slate-400">
          VaR is the potential 1-day loss; e.g. 95% historical means losses exceed this on ~1 day in 20.
        </p>
      </div>
    </Card>
  );
}
