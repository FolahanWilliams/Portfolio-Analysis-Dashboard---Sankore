import { api } from "../api/client";
import { useApi } from "../lib/useApi";
import type { Alert, WindowCode } from "../types/api";
import { Card, EmptyState, ErrorState, Loading } from "../components/ui";

function SeverityDot({ s }: { s: Alert["severity"] }) {
  const cls = s === "breach" ? "bg-negative" : "bg-amber-500";
  return <span className={`mt-1.5 inline-block h-2 w-2 shrink-0 rounded-full ${cls}`} />;
}

function AlertRow({ a }: { a: Alert }) {
  return (
    <li className="flex items-start gap-3 border-t border-slate-50 py-2.5 first:border-t-0">
      <SeverityDot s={a.severity} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span
            className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${
              a.severity === "breach"
                ? "bg-red-50 text-negative"
                : "bg-amber-50 text-amber-700"
            }`}
          >
            {a.severity}
          </span>
          <span className="text-[11px] font-medium uppercase tracking-wide text-slate-400">
            {a.category}
          </span>
        </div>
        <p className="mt-0.5 text-sm text-slate-700">{a.detail}</p>
      </div>
    </li>
  );
}

export function AlertsSection({ window }: { window: WindowCode }) {
  const { data, loading, error } = useApi(() => api.alerts(window), [window]);

  if (loading) return <Card title="Alerts"><Loading /></Card>;
  if (error) return <Card title="Alerts"><ErrorState message={error} /></Card>;
  if (!data) return <Card title="Alerts"><EmptyState message="No data" /></Card>;

  const { breach, warning } = data.counts;

  return (
    <Card
      title="Alerts"
      subtitle={`Rule-based limit checks · as of ${data.as_of}`}
      right={
        <div className="flex items-center gap-2">
          <span className="rounded-full bg-red-50 px-2 py-0.5 text-xs font-semibold text-negative">
            {breach} breach{breach === 1 ? "" : "es"}
          </span>
          <span className="rounded-full bg-amber-50 px-2 py-0.5 text-xs font-semibold text-amber-700">
            {warning} warning{warning === 1 ? "" : "s"}
          </span>
        </div>
      }
    >
      {data.alerts.length === 0 ? (
        <div className="py-6 text-center text-sm text-positive">
          All clear — no limits breached in this window.
        </div>
      ) : (
        <ul className="max-h-72 overflow-y-auto pr-1">
          {data.alerts.map((a) => (
            <AlertRow key={a.id} a={a} />
          ))}
        </ul>
      )}
    </Card>
  );
}
