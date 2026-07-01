import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api/client";
import { useApi } from "../lib/useApi";
import type { Attribution, SnapshotAttribution, WindowCode } from "../types/api";
import { Card, EmptyState, ErrorState, Loading, Pill, StatTile } from "../components/ui";
import { fmtPct, fmtSignedPct, signClass } from "../lib/format";

function SnapshotAttributionView({ data }: { data: SnapshotAttribution }) {
  const sectorData = data.sector_contribution.map((s) => ({
    name: s.sector,
    Contribution: s.contribution,
  }));
  const top = [...data.security_contribution].slice(0, 6);
  const bottom = [...data.security_contribution].slice(-6).reverse();

  return (
    <Card
      title="Contribution Analysis"
      subtitle={`As of ${data.as_of} · drivers of the −/+ return since cost`}
      right={<Pill tone="blue">snapshot</Pill>}
    >
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div>
          <h3 className="mb-2 text-xs font-semibold text-slate-500">Contribution by sector (to total return)</h3>
          <ResponsiveContainer width="100%" height={240}>
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
            {data.security_contribution.map((s) => (
              <tr key={s.ticker} className="border-t border-slate-50">
                <td className="py-1.5 font-medium text-slate-700">{s.ticker}</td>
                <td className="py-1.5 text-slate-500">{s.sector}</td>
                <td className="py-1.5 text-right tabular text-slate-600">{fmtPct(s.weight, 1)}</td>
                <td className={`py-1.5 text-right tabular ${signClass(s.return)}`}>{fmtSignedPct(s.return, 1)}</td>
                <td className={`py-1.5 text-right tabular font-medium ${signClass(s.contribution)}`}>{fmtSignedPct(s.contribution)}</td>
              </tr>
            ))}
            <tr className="border-t-2 border-slate-200 font-semibold">
              <td className="py-2 text-slate-700" colSpan={4}>Total return (since cost)</td>
              <td className={`py-2 text-right tabular ${signClass(data.total_return)}`}>{fmtSignedPct(data.total_return)}</td>
            </tr>
          </tbody>
        </table>
        <p className="mt-2 text-[11px] text-slate-400">
          Brinson allocation/selection and MTD/QTD/YTD returns need a benchmark return series — they appear once a price history is captured.
        </p>
      </div>
    </Card>
  );
}

export function AttributionSection({ window, live = false, refreshTick = 0 }: { window: WindowCode; live?: boolean; refreshTick?: number }) {
  const { data, loading, error } = useApi(() => api.attribution(window, live), [window, live, refreshTick]);

  if (loading) return <Card title="Performance Attribution"><Loading /></Card>;
  if (error) return <Card title="Performance Attribution"><ErrorState message={error} /></Card>;
  if (!data) return <Card title="Performance Attribution"><EmptyState message="No data" /></Card>;

  if ((data as SnapshotAttribution).mode === "snapshot") {
    return <SnapshotAttributionView data={data as SnapshotAttribution} />;
  }
  const d = data as Attribution;

  const periodData = d.period_returns.map((p) => ({
    name: p.period,
    Portfolio: p.portfolio,
    Benchmark: p.benchmark,
  }));
  const brinsonData = d.brinson.map((b) => ({
    name: b.sector,
    Allocation: b.allocation,
    Selection: b.selection,
  }));
  const t = d.brinson_totals;

  return (
    <Card title="Performance Attribution" subtitle={`As of ${d.as_of} · window ${d.window}`}>
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
              <Bar dataKey="Portfolio" fill="#2563eb" radius={3} isAnimationActive={false} />
              <Bar dataKey="Benchmark" fill="#cbd5e1" radius={3} isAnimationActive={false} />
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
              <Bar dataKey="Allocation" stackId="a" fill="#102a43" radius={[3, 3, 0, 0]} isAnimationActive={false} />
              <Bar dataKey="Selection" stackId="a" fill="#60a5fa" radius={[3, 3, 0, 0]} isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

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
            {d.brinson.map((b) => (
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
