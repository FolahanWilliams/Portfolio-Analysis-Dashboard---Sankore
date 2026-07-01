import type { ReactNode } from "react";
import { signClass } from "../lib/format";

export function Card({
  title,
  subtitle,
  right,
  children,
  className = "",
}: {
  title?: string;
  subtitle?: string;
  right?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`rounded-xl bg-white shadow-sm shadow-navy-900/5 ring-1 ring-slate-200/70 ${className}`}>
      {(title || right) && (
        <header className="flex items-center justify-between gap-3 border-b border-slate-100 px-5 py-3">
          <div>
            {title && (
              <h2 className="flex items-center gap-2 text-sm font-semibold text-navy">
                <span className="h-3.5 w-1 rounded-full bg-brand" />
                {title}
              </h2>
            )}
            {subtitle && <p className="ml-3 text-xs text-slate-400">{subtitle}</p>}
          </div>
          {right}
        </header>
      )}
      <div className="p-5">{children}</div>
    </section>
  );
}

export function StatTile({
  label,
  value,
  sub,
  tone = "neutral",
}: {
  label: string;
  value: ReactNode;
  sub?: ReactNode;
  tone?: "neutral" | "value";
}) {
  return (
    <div
      className={`rounded-lg px-4 py-3 ring-1 ${
        tone === "value"
          ? "bg-gradient-to-br from-navy-50 to-white ring-brand/20"
          : "bg-slate-50/70 ring-slate-200/60"
      }`}
    >
      <div className="text-[11px] font-medium uppercase tracking-wide text-slate-400">
        {label}
      </div>
      <div
        className={`mt-1 tabular text-2xl font-semibold ${
          tone === "value" ? "text-navy" : "text-slate-800"
        }`}
      >
        {value}
      </div>
      {sub && <div className="mt-0.5 text-xs tabular">{sub}</div>}
    </div>
  );
}

export function Delta({ value, text }: { value: number | null | undefined; text: string }) {
  return <span className={`tabular font-medium ${signClass(value)}`}>{text}</span>;
}

export function Pill({ children, tone = "slate", title }: { children: ReactNode; tone?: string; title?: string }) {
  const tones: Record<string, string> = {
    slate: "bg-slate-100 text-slate-600",
    amber: "bg-amber-100 text-amber-700",
    blue: "bg-blue-50 text-brand",
  };
  return (
    <span title={title} className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${tones[tone] ?? tones.slate}`}>
      {children}
    </span>
  );
}

export function Loading({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 py-10 text-sm text-slate-400">
      <span className="h-2 w-2 animate-pulse rounded-full bg-brand" />
      {label}...
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-negative/20 bg-red-50 px-4 py-6 text-sm text-negative">
      <div className="font-semibold">Couldn't load this view</div>
      <div className="mt-1 text-red-500">{message}</div>
    </div>
  );
}

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="py-10 text-center text-sm text-slate-400">{message}</div>
  );
}

export function TruncatedNote({ when }: { when: boolean }) {
  if (!when) return null;
  return (
    <Pill tone="amber">Window exceeds available history — measured from inception</Pill>
  );
}
