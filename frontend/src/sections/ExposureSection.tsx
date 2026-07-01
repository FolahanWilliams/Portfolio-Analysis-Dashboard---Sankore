import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api/client";
import { useApi } from "../lib/useApi";
import type { GroupWeight, WindowCode } from "../types/api";
import { Card, EmptyState, ErrorState, Loading, StatTile } from "../components/ui";
import { Matrix } from "../components/Matrix";
import { fmtNum, fmtPct, heatBlue } from "../lib/format";

function WeightChart({ rows, keyField }: { rows: GroupWeight[]; keyField: "sector" | "region" }) {
  const data = [...rows]
    .sort((a, b) => b.portfolio - a.portfolio)
    .map((r) => ({ name: (r[keyField] as string) ?? "", weight: r.portfolio }));
  const max = Math.max(0.01, ...data.map((d) => d.weight));
  return (
    <ResponsiveContainer width="100%" height={Math.max(120, data.length * 30)}>
      <BarChart data={data} layout="vertical" margin={{ left: 10, right: 44, top: 4, bottom: 4 }}>
        <XAxis type="number" domain={[0, max * 1.1]} tickFormatter={(v) => fmtPct(v, 0)}
          tick={{ fontSize: 11, fill: "#94a3b8" }} />
        <YAxis type="category" dataKey="name" width={116} tick={{ fontSize: 12, fill: "#475569" }} />
        <Tooltip formatter={(v: number) => [fmtPct(v, 1), "Weight"]}
          contentStyle={{ fontSize: 12, borderRadius: 8 }} />
        <Bar dataKey="weight" radius={3} isAnimationActive={false}>
          {data.map((_, i) => (
            <Cell key={i} fill="#2563eb" />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

function WeightTable({ rows, keyField }: { rows: GroupWeight[]; keyField: "sector" | "region" }) {
  const sorted = [...rows].sort((a, b) => b.portfolio - a.portfolio);
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-[11px] uppercase tracking-wide text-slate-400">
          <th className="py-1 text-left font-medium capitalize">{keyField}</th>
          <th className="py-1 text-right font-medium">Weight</th>
        </tr>
      </thead>
      <tbody>
        {sorted.map((r) => (
          <tr key={(r[keyField] as string) ?? ""} className="border-t border-slate-50">
            <td className="py-1.5 font-medium text-slate-700">{r[keyField]}</td>
            <td className="py-1.5 text-right tabular text-slate-600">{fmtPct(r.portfolio, 1)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function ExposureSection({ window, live = false, refreshTick = 0 }: { window: WindowCode; live?: boolean; refreshTick?: number }) {
  const { data, loading, error } = useApi(() => api.exposure(window, live), [window, live, refreshTick]);

  if (loading) return <Card title="Sector & Geographic Exposure"><Loading /></Card>;
  if (error) return <Card title="Sector & Geographic Exposure"><ErrorState message={error} /></Card>;
  if (!data) return <Card title="Sector & Geographic Exposure"><EmptyState message="No data" /></Card>;

  const maxW = Math.max(...data.heatmap.values.flat(), 0.0001);

  return (
    <Card
      title="Sector & Geographic Exposure"
      subtitle={`Where the fund's money sits · as of ${data.as_of}`}
    >
      <div className="grid grid-cols-3 gap-3">
        <StatTile
          label="Effective holdings"
          value={fmtNum(data.concentration.effective_n, 1)}
          sub={<span className="text-slate-400">higher = more spread out</span>}
          tone="value"
        />
        <StatTile
          label="Largest position"
          value={fmtPct(data.concentration.largest_weight, 1)}
          sub={<span className="text-slate-400">single biggest stock</span>}
        />
        <StatTile
          label="Top-5 holdings"
          value={fmtPct(data.concentration.top5_weight, 1)}
          sub={<span className="text-slate-400">of the whole book</span>}
        />
      </div>

      {/* By-sector breakdown on the left; sector x region map beside it on the right */}
      <div className="mt-6 grid grid-cols-1 gap-8 lg:grid-cols-2">
        <div>
          <h3 className="text-sm font-semibold text-navy">By sector</h3>
          <p className="mb-2 text-xs text-slate-400">Share of the portfolio in each sector (largest first).</p>
          <WeightChart rows={data.sector} keyField="sector" />
          <div className="mt-3"><WeightTable rows={data.sector} keyField="sector" /></div>
        </div>
        <div>
          <h3 className="text-sm font-semibold text-navy">Sector × region map</h3>
          <p className="mb-2 text-xs text-slate-400">
            % of the portfolio in each sector/region — darker means more money there.
          </p>
          <Matrix
            rowHeader="Sector"
            rowLabels={data.heatmap.sectors}
            colLabels={data.heatmap.regions}
            values={data.heatmap.values}
            color={(v) => heatBlue(v, maxW)}
            format={(v) => (v > 0 ? fmtPct(v, 1) : "·")}
          />
        </div>
      </div>

      <div className="mt-8 lg:w-1/2 lg:pr-4">
        <h3 className="text-sm font-semibold text-navy">By region</h3>
        <p className="mb-2 text-xs text-slate-400">Geographic split of the portfolio.</p>
        <WeightChart rows={data.region} keyField="region" />
        <div className="mt-3"><WeightTable rows={data.region} keyField="region" /></div>
      </div>
    </Card>
  );
}
