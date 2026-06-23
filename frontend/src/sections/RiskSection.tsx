import { api } from "../api/client";
import { useApi } from "../lib/useApi";
import type { WindowCode } from "../types/api";
import { Card, EmptyState, ErrorState, Loading, StatTile, TruncatedNote } from "../components/ui";
import { Matrix } from "../components/Matrix";
import { fmtNum, fmtPct, signClass } from "../lib/format";

function corrColor(v: number): string {
  // -1 (red) .. 0 (white) .. 1 (blue)
  if (v >= 0) return `hsl(213, 70%, ${96 - v * 50}%)`;
  return `hsl(0, 65%, ${96 - -v * 46}%)`;
}

export function RiskSection({ window }: { window: WindowCode }) {
  const { data, loading, error } = useApi(() => api.risk(window), [window]);

  if (loading) return <Card title="Risk Metrics"><Loading /></Card>;
  if (error) return <Card title="Risk Metrics"><ErrorState message={error} /></Card>;
  if (!data) return <Card title="Risk Metrics"><EmptyState message="No data" /></Card>;

  const var95 = data.var["95"];
  const var99 = data.var["99"];

  return (
    <Card
      title="Risk Metrics"
      subtitle={`As of ${data.as_of} · ${data.observations} obs · rf ${fmtPct(data.risk_free_rate, 1)}`}
      right={<TruncatedNote when={data.truncated} />}
    >
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatTile label="Volatility (ann.)" value={fmtPct(data.volatility, 1)} tone="value" />
        <StatTile label="Beta" value={fmtNum(data.beta, 2)} />
        <StatTile
          label="Sharpe"
          value={<span className={signClass(data.sharpe)}>{fmtNum(data.sharpe, 2)}</span>}
        />
        <StatTile label="Max drawdown" value={<span className="text-negative">{fmtPct(data.max_drawdown, 1)}</span>} />
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
            rowLabels={data.correlation.tickers}
            colLabels={data.correlation.tickers}
            values={data.correlation.matrix}
            color={corrColor}
            format={(v) => v.toFixed(2)}
            cellSize={34}
          />
        </div>
      </div>
    </Card>
  );
}
