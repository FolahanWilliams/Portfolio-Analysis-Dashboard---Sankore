import { api } from "../api/client";
import { useApi } from "../lib/useApi";
import type { Contribution, WindowCode } from "../types/api";
import { Card, EmptyState, ErrorState, Loading, StatTile, TruncatedNote } from "../components/ui";
import { fmtMoney, fmtSignedPct, signClass } from "../lib/format";

function ContribRow({ c }: { c: Contribution }) {
  const max = 0.06; // scale bar to a sensible contribution magnitude
  // Half-width bars diverge from a centre line; cap at 50% so they never
  // overflow the track into the return column.
  const w = Math.min(Math.abs(c.contribution) / max, 1) * 50;
  return (
    <div className="flex items-center gap-3 py-1.5">
      <div className="w-16 shrink-0 truncate text-sm font-medium" title={c.name}>
        <span className="text-slate-600">{c.ticker}</span>
      </div>
      <div className="relative h-2 flex-1 overflow-hidden rounded bg-slate-100">
        <div
          className={`absolute top-0 h-2 ${c.contribution >= 0 ? "bg-positive" : "bg-negative"}`}
          style={{ width: `${w}%`, left: c.contribution >= 0 ? "50%" : `${50 - w}%` }}
        />
        <div className="absolute left-1/2 top-0 h-2 w-px bg-slate-300" />
      </div>
      <div className="w-16 shrink-0 text-right text-xs tabular text-slate-500">{fmtSignedPct(c.return)}</div>
      <div className={`w-16 shrink-0 text-right text-xs tabular font-medium ${signClass(c.contribution)}`}>
        {fmtSignedPct(c.contribution)}
      </div>
    </div>
  );
}

export function SummarySection({ window, live = false, refreshTick = 0 }: { window: WindowCode; live?: boolean; refreshTick?: number }) {
  const { data, loading, error } = useApi(() => api.summary(window, live), [window, live, refreshTick]);

  if (loading) return <Card title="Portfolio Summary"><Loading /></Card>;
  if (error) return <Card title="Portfolio Summary"><ErrorState message={error} /></Card>;
  if (!data) return <Card title="Portfolio Summary"><EmptyState message="No data" /></Card>;

  const snapshot = data.mode === "snapshot";
  return (
    <Card
      title="Portfolio Summary"
      subtitle={`As of ${data.as_of} · base ${data.base_currency}`}
      right={<TruncatedNote when={data.truncated} />}
    >
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatTile label="AUM" value={fmtMoney(data.aum)} tone="value" />
        <StatTile
          label={snapshot ? "Return (since cost)" : `Total return (${data.window})`}
          value={<span className={signClass(data.total_return)}>{fmtSignedPct(data.total_return)}</span>}
          sub={
            data.benchmark_return != null
              ? <span className="text-slate-400">Benchmark {fmtSignedPct(data.benchmark_return)}</span>
              : data.cost_basis != null
                ? <span className="text-slate-400">Cost {fmtMoney(data.cost_basis)}</span>
                : undefined
          }
        />
        {snapshot ? (
          <StatTile
            label="Positions at a loss"
            value={`${data.positions_at_loss ?? 0} / ${data.holdings_count}`}
          />
        ) : (
          <StatTile
            label="Active vs benchmark"
            value={<span className={signClass(data.active_return)}>{fmtSignedPct(data.active_return)}</span>}
          />
        )}
        <StatTile
          label="Unrealised P&L"
          value={<span className={signClass(data.pnl.unrealised)}>{fmtMoney(data.pnl.unrealised)}</span>}
          sub={<span className="text-slate-400">Realised {fmtMoney(data.pnl.realised)}</span>}
        />
      </div>

      <div className="mt-5 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div>
          <div className="mb-1 flex items-center gap-3 text-[11px] font-semibold uppercase tracking-wide text-slate-400">
            <span className="flex-1">Top contributors</span>
            <span className="w-16 shrink-0 text-right">return</span>
            <span className="w-16 shrink-0 text-right">contrib</span>
          </div>
          {data.top_contributors.map((c) => <ContribRow key={c.ticker} c={c} />)}
        </div>
        <div>
          <div className="mb-1 flex items-center gap-3 text-[11px] font-semibold uppercase tracking-wide text-slate-400">
            <span className="flex-1">Top detractors</span>
            <span className="w-16 shrink-0 text-right">return</span>
            <span className="w-16 shrink-0 text-right">contrib</span>
          </div>
          {data.top_detractors.map((c) => <ContribRow key={c.ticker} c={c} />)}
        </div>
      </div>
    </Card>
  );
}
