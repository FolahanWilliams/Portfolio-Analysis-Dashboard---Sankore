import { useMemo, useState } from "react";
import { api } from "../api/client";
import { useApi } from "../lib/useApi";
import type { Holding, WindowCode } from "../types/api";
import { Card, EmptyState, ErrorState, Loading } from "../components/ui";
import { fmtMoney, fmtNum, fmtPrice, fmtSignedPct, signClass } from "../lib/format";

type SortKey = "weight" | "unrealised_return" | "ticker";

export function HoldingsSection({
  window,
  live = false,
  refreshTick = 0,
}: {
  window: WindowCode;
  live?: boolean;
  refreshTick?: number;
}) {
  const { data, loading, error } = useApi(() => api.holdings(window, live), [window, live, refreshTick]);
  const [sort, setSort] = useState<SortKey>("weight");

  const rows = useMemo(() => {
    const hs = data?.holdings ? [...data.holdings] : [];
    hs.sort((a, b) => {
      if (sort === "ticker") return a.ticker.localeCompare(b.ticker);
      const av = (a[sort] as number | null) ?? -Infinity;
      const bv = (b[sort] as number | null) ?? -Infinity;
      return bv - av;
    });
    return hs;
  }, [data, sort]);

  if (loading) return <Card title="Holdings — price & P&L"><Loading /></Card>;
  if (error) return <Card title="Holdings — price & P&L"><ErrorState message={error} /></Card>;
  if (!data || rows.length === 0)
    return <Card title="Holdings — price & P&L"><EmptyState message="No holdings" /></Card>;

  const Th = ({ label, k, className = "" }: { label: string; k?: SortKey; className?: string }) => (
    <th
      className={`whitespace-nowrap px-3 py-2 text-[11px] font-semibold uppercase tracking-wide text-slate-400 ${
        k ? "cursor-pointer select-none hover:text-brand" : ""
      } ${className}`}
      onClick={k ? () => setSort(k) : undefined}
      title={k ? "Click to sort" : undefined}
    >
      {label}
      {k && sort === k ? " ↓" : ""}
    </th>
  );

  return (
    <Card
      title="Holdings — price & P&L"
      subtitle={`${data.holdings_count} positions · as of ${data.as_of} · bought price vs current price`}
    >
      <div className="max-h-[520px] overflow-auto rounded-lg ring-1 ring-slate-100">
        <table className="w-full border-collapse text-sm">
          <thead className="sticky top-0 z-10 bg-slate-50/95 backdrop-blur">
            <tr className="border-b border-slate-200 text-left">
              <Th label="Stock" k="ticker" className="text-left" />
              <Th label="Shares" className="text-right" />
              <Th label="Bought" className="text-right" />
              <Th label="Current" className="text-right" />
              <Th label="Change" k="unrealised_return" className="text-right" />
              <Th label="Market value" className="text-right" />
              <Th label="Unrealised P&L" className="text-right" />
              <Th label="Weight" k="weight" className="text-right" />
            </tr>
          </thead>
          <tbody>
            {rows.map((h: Holding) => (
              <tr key={h.ticker} className="border-b border-slate-50 last:border-0 hover:bg-slate-50/60">
                <td className="px-3 py-2">
                  <div className="font-semibold text-navy">{h.ticker}</div>
                  <div className="max-w-[220px] truncate text-xs text-slate-400" title={`${h.name} · ${h.sector} · ${h.region}`}>
                    {h.name}
                  </div>
                </td>
                <td className="px-3 py-2 text-right tabular text-slate-600">{fmtNum(h.shares, 0)}</td>
                <td className="px-3 py-2 text-right tabular text-slate-500">{fmtPrice(h.cost_price, h.currency)}</td>
                <td className="px-3 py-2 text-right tabular font-medium text-navy">{fmtPrice(h.current_price, h.currency)}</td>
                <td className={`px-3 py-2 text-right tabular font-medium ${signClass(h.unrealised_return)}`}>
                  {fmtSignedPct(h.unrealised_return)}
                </td>
                <td className="px-3 py-2 text-right tabular text-slate-700">{fmtMoney(h.market_value)}</td>
                <td className={`px-3 py-2 text-right tabular ${signClass(h.unrealised_pnl)}`}>{fmtMoney(h.unrealised_pnl)}</td>
                <td className="px-3 py-2 text-right tabular text-slate-600">{fmtNum((h.weight ?? 0) * 100, 1)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-2 text-xs text-slate-400">
        “Bought” is the average purchase price from the holdings sheet; “Current” is the latest price
        {live ? " (live from Yahoo Finance)" : ""}. Change is the gain/loss since purchase. Click a column header to sort.
      </p>
    </Card>
  );
}
