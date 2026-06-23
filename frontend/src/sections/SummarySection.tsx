import { api } from "../api/client";
import { useApi } from "../lib/useApi";
import type { Contribution, WindowCode } from "../types/api";
import { Card, EmptyState, ErrorState, Loading, StatTile, TruncatedNote } from "../components/ui";
import { fmtMoney, fmtSignedPct, signClass } from "../lib/format";

function ContribRow({ c }: { c: Contribution }) {
  const max = 0.06; // scale bar to a sensible contribution magnitude
  const w = Math.min(Math.abs(c.contribution) / max, 1) * 100;
  return (
    <div className="flex items-center gap-3 py-1.5">
      <div className="w-32 truncate text-sm font-medium text-slate-700" title={c.name}>
        <span className="text-slate-400">{c.ticker}</span>
      </div>
      <div className="relative h-2 flex-1 rounded bg-slate-100">
        <div
          className={`absolute top-0 h-2 rounded ${c.contribution >= 0 ? "bg-positive" : "bg-negative"}`}
          style={{ width: `${w}%`, left: c.contribution >= 0 ? "50%" : `${50 - w / 2}%` }}
        />
        <div className="absolute left-1/2 top-0 h-2 w-px bg-slate-300" />
      </div>
      <div className="w-20 text-right text-xs tabular text-slate-500">{fmtSignedPct(c.return)}</div>
      <div className={`w-20 text-right text-xs tabular font-medium ${signClass(c.contribution)}`}>
        {fmtSignedPct(c.contribution)}
      </div>
    </div>
  );
}

export function SummarySection({ window }: { window: WindowCode }) {
  const { data, loading, error } = useApi(() => api.summary(window), [window]);

  if (loading) return <Card title="Portfolio Summary"><Loading /></Card>;
  if (error) return <Card title="Portfolio Summary"><ErrorState message={error} /></Card>;
  if (!data) return <Card title="Portfolio Summary"><EmptyState message="No data" /></Card>;

  return (
    <Card
      title="Portfolio Summary"
      subtitle={`As of ${data.as_of} · base ${data.base_currency}`}
      right={<TruncatedNote when={data.truncated} />}
    >
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatTile label="AUM" value={fmtMoney(data.aum)} tone="value" />
        <StatTile
          label={`Total return (${data.window})`}
          value={<span className={signClass(data.total_return)}>{fmtSignedPct(data.total_return)}</span>}
          sub={<span className="text-slate-400">Benchmark {fmtSignedPct(data.benchmark_return)}</span>}
        />
        <StatTile
          label="Active vs benchmark"
          value={<span className={signClass(data.active_return)}>{fmtSignedPct(data.active_return)}</span>}
        />
        <StatTile
          label="Unrealised P&L"
          value={<span className={signClass(data.pnl.unrealised)}>{fmtMoney(data.pnl.unrealised)}</span>}
          sub={<span className="text-slate-400">Realised {fmtMoney(data.pnl.realised)}</span>}
        />
      </div>

      <div className="mt-5 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div>
          <div className="mb-1 flex items-center justify-between text-xs font-semibold text-slate-500">
            <span>Top contributors</span>
            <span className="flex gap-6"><span>return</span><span>contrib</span></span>
          </div>
          {data.top_contributors.map((c) => <ContribRow key={c.ticker} c={c} />)}
        </div>
        <div>
          <div className="mb-1 flex items-center justify-between text-xs font-semibold text-slate-500">
            <span>Top detractors</span>
            <span className="flex gap-6"><span>return</span><span>contrib</span></span>
          </div>
          {data.top_detractors.map((c) => <ContribRow key={c.ticker} c={c} />)}
        </div>
      </div>
    </Card>
  );
}
