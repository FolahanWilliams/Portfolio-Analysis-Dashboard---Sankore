import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api/client";
import { useApi } from "../lib/useApi";
import type { Attribution, WindowCode } from "../types/api";
import { Card, EmptyState, ErrorState, Loading } from "../components/ui";
import { fmtPct, fmtSignedPct, signClass } from "../lib/format";

export function AttributionSection({ window, live = false, refreshTick = 0 }: { window: WindowCode; live?: boolean; refreshTick?: number }) {
  const { data, loading, error } = useApi(() => api.attribution(window, live), [window, live, refreshTick]);

  if (loading) return <Card title="Performance Attribution"><Loading /></Card>;
  if (error) return <Card title="Performance Attribution"><ErrorState message={error} /></Card>;
  if (!data) return <Card title="Performance Attribution"><EmptyState message="No data" /></Card>;

  const d = data as Attribution;
  const sectorData = d.sector_contribution.map((s) => ({ name: s.sector, Contribution: s.contribution }));
  const top = [...d.security_contribution].slice(0, 6);
  const bottom = [...d.security_contribution].slice(-6).reverse();

  return (
    <Card
      title="Performance Attribution"
      subtitle={`Inception-to-date · what drives the ${fmtSignedPct(d.total_return, 2)} return since purchase (gain$ ÷ cost basis)`}
    >
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div>
          <h3 className="mb-2 text-xs font-semibold text-slate-500">Contribution by sector (to total return)</h3>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={sectorData} layout="vertical" margin={{ left: 8, right: 16, top: 4, bottom: 4 }}>
              <CartesianGrid horizontal={false} stroke="#f1f5f9" />
              <XAxis type="number" tickFormatter={(v) => fmtPct(v, 1)} tick={{ fontSize: 11, fill: "#94a3b8" }} />
              <YAxis type="category" dataKey="name" width={130} tick={{ fontSize: 11, fill: "#475569" }} />
              <Tooltip formatter={(v: number) => [fmtSignedPct(v), "Contribution"]} contentStyle={{ fontSize: 12, borderRadius: 8 }} />
              <ReferenceLine x={0} stroke="#cbd5e1" />
              <Bar dataKey="Contribution" radius={3} isAnimationActive={false}>
                {sectorData.map((s, i) => (
                  <Cell key={i} fill={s.Contribution >= 0 ? "#059669" : "#dc2626"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="grid grid-cols-2 gap-6">
          <div>
            <h4 className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-positive">Top adders</h4>
            {top.map((s) => (
              <div key={s.ticker} className="flex items-center justify-between py-1 text-sm">
                <span className="font-medium text-slate-600">{s.ticker}</span>
                <span className={`tabular ${signClass(s.contribution)}`}>{fmtSignedPct(s.contribution)}</span>
              </div>
            ))}
          </div>
          <div>
            <h4 className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-negative">Top drags</h4>
            {bottom.map((s) => (
              <div key={s.ticker} className="flex items-center justify-between py-1 text-sm">
                <span className="font-medium text-slate-600">{s.ticker}</span>
                <span className={`tabular ${signClass(s.contribution)}`}>{fmtSignedPct(s.contribution)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-6 overflow-x-auto">
        <h3 className="mb-2 text-xs font-semibold text-slate-500">Contribution detail by holding</h3>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-[11px] uppercase tracking-wide text-slate-400">
              <th className="py-1 text-left font-medium">Holding</th>
              <th className="py-1 text-left font-medium">Sector</th>
              <th className="py-1 text-right font-medium">Weight</th>
              <th className="py-1 text-right font-medium">Return</th>
              <th className="py-1 text-right font-medium">Contribution</th>
            </tr>
          </thead>
          <tbody>
            {d.security_contribution.map((s) => (
              <tr key={s.ticker} className="border-t border-slate-50">
                <td className="py-1.5 font-medium text-slate-700">{s.ticker}</td>
                <td className="py-1.5 text-slate-500">{s.sector}</td>
                <td className="py-1.5 text-right tabular text-slate-600">{fmtPct(s.weight, 1)}</td>
                <td className={`py-1.5 text-right tabular ${signClass(s.return)}`}>{fmtSignedPct(s.return, 1)}</td>
                <td className={`py-1.5 text-right tabular font-medium ${signClass(s.contribution)}`}>{fmtSignedPct(s.contribution)}</td>
              </tr>
            ))}
            <tr className="border-t-2 border-slate-200 font-semibold">
              <td className="py-2 text-slate-700" colSpan={4}>Total return (since purchase)</td>
              <td className={`py-2 text-right tabular ${signClass(d.total_return)}`}>{fmtSignedPct(d.total_return)}</td>
            </tr>
          </tbody>
        </table>
        <p className="mt-2 text-[11px] text-slate-400">
          Each holding’s contribution = its gain$ ÷ total cost basis; the column sums to the book’s total return.
          Return vs the S&P 500 (alpha, beta, excess) is on the Performance &amp; Risk panel.
        </p>
      </div>
    </Card>
  );
}
