import {
  Bar,
  BarChart,
  Cell,
  ReferenceLine,
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
import { fmtNum, fmtPct, fmtSignedPct, heatBlue, signClass } from "../lib/format";

function ActiveWeightChart({ rows, keyField }: { rows: GroupWeight[]; keyField: "sector" | "region" }) {
  const data = rows.map((r) => ({
    name: (r[keyField] as string) ?? "",
    active: r.active,
  }));
  const max = Math.max(0.01, ...data.map((d) => Math.abs(d.active)));
  return (
    <ResponsiveContainer width="100%" height={Math.max(120, data.length * 34)}>
      <BarChart data={data} layout="vertical" margin={{ left: 10, right: 24, top: 4, bottom: 4 }}>
        <XAxis type="number" domain={[-max * 1.15, max * 1.15]} tickFormatter={(v) => fmtPct(v, 0)}
          tick={{ fontSize: 11, fill: "#94a3b8" }} />
        <YAxis type="category" dataKey="name" width={96} tick={{ fontSize: 12, fill: "#475569" }} />
        <Tooltip formatter={(v: number) => [fmtSignedPct(v), "Active weight"]}
          contentStyle={{ fontSize: 12, borderRadius: 8 }} />
        <ReferenceLine x={0} stroke="#cbd5e1" />
        <Bar dataKey="active" radius={3} isAnimationActive={false}>
          {data.map((d, i) => (
            <Cell key={i} fill={d.active >= 0 ? "#059669" : "#dc2626"} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

function WeightTable({ rows, keyField }: { rows: GroupWeight[]; keyField: "sector" | "region" }) {
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-[11px] uppercase tracking-wide text-slate-400">
          <th className="py-1 text-left font-medium capitalize">{keyField}</th>
          <th className="py-1 text-right font-medium">Port.</th>
          <th className="py-1 text-right font-medium">Bench.</th>
          <th className="py-1 text-right font-medium">Active</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={(r[keyField] as string) ?? ""} className="border-t border-slate-50">
            <td className="py-1.5 font-medium text-slate-700">{r[keyField]}</td>
            <td className="py-1.5 text-right tabular text-slate-600">{fmtPct(r.portfolio)}</td>
            <td className="py-1.5 text-right tabular text-slate-500">{fmtPct(r.benchmark)}</td>
            <td className={`py-1.5 text-right tabular font-medium ${signClass(r.active)}`}>
              {fmtSignedPct(r.active)}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function ExposureSection({ window }: { window: WindowCode }) {
  const { data, loading, error } = useApi(() => api.exposure(window), [window]);

  if (loading) return <Card title="Sector & Geographic Exposure"><Loading /></Card>;
  if (error) return <Card title="Sector & Geographic Exposure"><ErrorState message={error} /></Card>;
  if (!data) return <Card title="Sector & Geographic Exposure"><EmptyState message="No data" /></Card>;

  const maxW = Math.max(...data.heatmap.values.flat(), 0.0001);

  return (
    <Card title="Sector & Geographic Exposure" subtitle={`As of ${data.as_of}`}>
      <div className="grid grid-cols-3 gap-3">
        <StatTile label="Effective N" value={fmtNum(data.concentration.effective_n, 1)} tone="value" />
        <StatTile label="HHI" value={fmtNum(data.concentration.hhi, 3)} />
        <StatTile label="Top-5 weight" value={fmtPct(data.concentration.top5_weight, 1)} />
      </div>

      <div className="mt-5 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div>
          <h3 className="mb-2 text-xs font-semibold text-slate-500">Active weight by sector</h3>
          <ActiveWeightChart rows={data.sector} keyField="sector" />
          <div className="mt-3"><WeightTable rows={data.sector} keyField="sector" /></div>
        </div>
        <div>
          <h3 className="mb-2 text-xs font-semibold text-slate-500">Active weight by region</h3>
          <ActiveWeightChart rows={data.region} keyField="region" />
          <div className="mt-3"><WeightTable rows={data.region} keyField="region" /></div>
        </div>
      </div>

      <div className="mt-6">
        <h3 className="mb-2 text-xs font-semibold text-slate-500">Exposure heatmap (portfolio weight, sector × region)</h3>
        <Matrix
          rowHeader="Sector"
          rowLabels={data.heatmap.sectors}
          colLabels={data.heatmap.regions}
          values={data.heatmap.values}
          color={(v) => heatBlue(v, maxW)}
          format={(v) => (v > 0 ? fmtPct(v, 1) : "·")}
        />
      </div>
    </Card>
  );
}
