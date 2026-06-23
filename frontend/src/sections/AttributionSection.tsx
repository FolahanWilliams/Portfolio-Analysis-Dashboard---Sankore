import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api/client";
import { useApi } from "../lib/useApi";
import type { WindowCode } from "../types/api";
import { Card, EmptyState, ErrorState, Loading, StatTile } from "../components/ui";
import { fmtPct, fmtSignedPct, signClass } from "../lib/format";

export function AttributionSection({ window }: { window: WindowCode }) {
  const { data, loading, error } = useApi(() => api.attribution(window), [window]);

  if (loading) return <Card title="Performance Attribution"><Loading /></Card>;
  if (error) return <Card title="Performance Attribution"><ErrorState message={error} /></Card>;
  if (!data) return <Card title="Performance Attribution"><EmptyState message="No data" /></Card>;

  const periodData = data.period_returns.map((p) => ({
    name: p.period,
    Portfolio: p.portfolio,
    Benchmark: p.benchmark,
  }));

  const brinsonData = data.brinson.map((b) => ({
    name: b.sector,
    Allocation: b.allocation,
    Selection: b.selection,
  }));

  const t = data.brinson_totals;

  return (
    <Card title="Performance Attribution" subtitle={`As of ${data.as_of} · window ${data.window}`}>
      {/* Brinson totals: the headline of why we beat / lagged the benchmark */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatTile label="Allocation" value={<span className={signClass(t.allocation)}>{fmtSignedPct(t.allocation)}</span>} />
        <StatTile label="Selection" value={<span className={signClass(t.selection)}>{fmtSignedPct(t.selection)}</span>} />
        <StatTile label="Interaction" value={<span className={signClass(t.interaction)}>{fmtSignedPct(t.interaction)}</span>} />
        <StatTile label="Total active" value={<span className={signClass(t.total)}>{fmtSignedPct(t.total)}</span>} tone="value" />
      </div>

      <div className="mt-5 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div>
          <h3 className="mb-2 text-xs font-semibold text-slate-500">Returns by period</h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={periodData} margin={{ left: 0, right: 8, top: 8, bottom: 4 }}>
              <CartesianGrid vertical={false} stroke="#f1f5f9" />
              <XAxis dataKey="name" tick={{ fontSize: 12, fill: "#475569" }} />
              <YAxis tickFormatter={(v) => fmtPct(v, 0)} tick={{ fontSize: 11, fill: "#94a3b8" }} width={40} />
              <Tooltip formatter={(v: number) => fmtSignedPct(v)} contentStyle={{ fontSize: 12, borderRadius: 8 }} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <ReferenceLine y={0} stroke="#cbd5e1" />
              <Bar dataKey="Portfolio" fill="#1f6feb" radius={3} />
              <Bar dataKey="Benchmark" fill="#94a3b8" radius={3} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div>
          <h3 className="mb-2 text-xs font-semibold text-slate-500">Brinson by sector (allocation vs selection)</h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={brinsonData} margin={{ left: 0, right: 8, top: 8, bottom: 4 }}>
              <CartesianGrid vertical={false} stroke="#f1f5f9" />
              <XAxis dataKey="name" tick={{ fontSize: 11, fill: "#475569" }} />
              <YAxis tickFormatter={(v) => fmtPct(v, 1)} tick={{ fontSize: 11, fill: "#94a3b8" }} width={48} />
              <Tooltip formatter={(v: number) => fmtSignedPct(v)} contentStyle={{ fontSize: 12, borderRadius: 8 }} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <ReferenceLine y={0} stroke="#cbd5e1" />
              <Bar dataKey="Allocation" stackId="a" fill="#0f2c4d" radius={[3, 3, 0, 0]} />
              <Bar dataKey="Selection" stackId="a" fill="#38bdf8" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Detailed Brinson + sector contribution table */}
      <div className="mt-6 overflow-x-auto">
        <h3 className="mb-2 text-xs font-semibold text-slate-500">Attribution detail by sector</h3>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-[11px] uppercase tracking-wide text-slate-400">
              <th className="py-1 text-left font-medium">Sector</th>
              <th className="py-1 text-right font-medium">Port. wt</th>
              <th className="py-1 text-right font-medium">Bench. wt</th>
              <th className="py-1 text-right font-medium">Port. ret</th>
              <th className="py-1 text-right font-medium">Bench. ret</th>
              <th className="py-1 text-right font-medium">Alloc.</th>
              <th className="py-1 text-right font-medium">Select.</th>
              <th className="py-1 text-right font-medium">Total</th>
            </tr>
          </thead>
          <tbody>
            {data.brinson.map((b) => (
              <tr key={b.sector} className="border-t border-slate-50">
                <td className="py-1.5 font-medium text-slate-700">{b.sector}</td>
                <td className="py-1.5 text-right tabular text-slate-600">{fmtPct(b.w_portfolio, 1)}</td>
                <td className="py-1.5 text-right tabular text-slate-500">{fmtPct(b.w_benchmark, 1)}</td>
                <td className="py-1.5 text-right tabular text-slate-600">{fmtSignedPct(b.r_portfolio, 1)}</td>
                <td className="py-1.5 text-right tabular text-slate-500">{fmtSignedPct(b.r_benchmark, 1)}</td>
                <td className={`py-1.5 text-right tabular ${signClass(b.allocation)}`}>{fmtSignedPct(b.allocation)}</td>
                <td className={`py-1.5 text-right tabular ${signClass(b.selection)}`}>{fmtSignedPct(b.selection)}</td>
                <td className={`py-1.5 text-right tabular font-medium ${signClass(b.total)}`}>{fmtSignedPct(b.total)}</td>
              </tr>
            ))}
            <tr className="border-t-2 border-slate-200 font-semibold">
              <td className="py-2 text-slate-700">Total</td>
              <td colSpan={4} />
              <td className={`py-2 text-right tabular ${signClass(t.allocation)}`}>{fmtSignedPct(t.allocation)}</td>
              <td className={`py-2 text-right tabular ${signClass(t.selection)}`}>{fmtSignedPct(t.selection)}</td>
              <td className={`py-2 text-right tabular ${signClass(t.total)}`}>{fmtSignedPct(t.total)}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </Card>
  );
}
