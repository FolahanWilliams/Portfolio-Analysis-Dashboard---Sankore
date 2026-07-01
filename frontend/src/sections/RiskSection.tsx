import { api } from "../api/client";
import { useApi } from "../lib/useApi";
import type { Risk, SnapshotRisk, WindowCode } from "../types/api";
import { Card, EmptyState, ErrorState, Loading, Pill, StatTile, TruncatedNote } from "../components/ui";
import { Matrix } from "../components/Matrix";
import { fmtMoney, fmtNum, fmtPct, fmtSignedPct, signClass } from "../lib/format";

function corrColor(v: number): string {
  // -1 (red) .. 0 (white) .. 1 (blue)
  if (v >= 0) return `hsl(217, 72%, ${97 - v * 52}%)`;
  return `hsl(2, 62%, ${97 - -v * 46}%)`;
}

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
      title="Risk Metrics"
      subtitle={`As of ${d.as_of} · ${d.observations} obs · rf ${fmtPct(d.risk_free_rate, 1)}`}
      right={<TruncatedNote when={d.truncated} />}
    >
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatTile label="Volatility (ann.)" value={fmtPct(d.volatility, 1)} tone="value" />
        <StatTile label="Beta" value={fmtNum(d.beta, 2)} />
        <StatTile
          label="Sharpe"
          value={<span className={signClass(d.sharpe)}>{fmtNum(d.sharpe, 2)}</span>}
        />
        <StatTile label="Max drawdown" value={<span className="text-negative">{fmtPct(d.max_drawdown, 1)}</span>} />
      </div>

      <div className="mt-5 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div>
          <h3 className="mb-2 text-xs font-semibold text-slate-500">Value at Risk (1-day)</h3>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-[11px] uppercase tracking-wide text-slate-400">
                <th className="py-1 text-left font-medium">Confidence</th>
                <th className="py-1 text-right font-medium">Historical</th>
                <th className="py-1 text-right font-medium">Parametric</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-t border-slate-50">
                <td className="py-2 font-medium text-slate-700">95%</td>
                <td className="py-2 text-right tabular text-negative">{fmtPct(var95.historical, 2)}</td>
                <td className="py-2 text-right tabular text-negative">{fmtPct(var95.parametric, 2)}</td>
              </tr>
              <tr className="border-t border-slate-50">
                <td className="py-2 font-medium text-slate-700">99%</td>
                <td className="py-2 text-right tabular text-negative">{fmtPct(var99.historical, 2)}</td>
                <td className="py-2 text-right tabular text-negative">{fmtPct(var99.parametric, 2)}</td>
              </tr>
            </tbody>
          </table>
          <p className="mt-2 text-[11px] text-slate-400">
            VaR shown as the potential 1-day loss; e.g. 95% historical means losses exceed this on ~1 day in 20.
          </p>
        </div>

        <div>
          <h3 className="mb-2 text-xs font-semibold text-slate-500">Holdings correlation</h3>
          <Matrix
            rowLabels={d.correlation.tickers}
            colLabels={d.correlation.tickers}
            values={d.correlation.matrix}
            color={corrColor}
            format={(v) => v.toFixed(2)}
            cellSize={34}
          />
        </div>
      </div>
    </Card>
  );
}
