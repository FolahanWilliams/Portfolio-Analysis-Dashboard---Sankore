import type { ReactNode } from "react";
import type { Meta, WindowCode } from "../types/api";
import { Pill } from "./ui";

const WINDOW_LABELS: Record<WindowCode, string> = {
  MTD: "MTD",
  QTD: "QTD",
  YTD: "YTD",
  "1Y": "1Y",
  ALL: "All",
};

export function Shell({
  meta,
  window,
  onWindow,
  children,
}: {
  meta: Meta | null;
  window: WindowCode;
  onWindow: (w: WindowCode) => void;
  children: ReactNode;
}) {
  const windows = meta?.windows ?? (["MTD", "QTD", "YTD", "1Y", "ALL"] as WindowCode[]);
  const dq = meta?.data_quality;

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-10 border-b-2 border-brand/70 bg-gradient-to-r from-navy-900 via-navy to-navy-800 text-white shadow-md">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-6 py-3">
          <div className="flex items-baseline gap-3">
            <h1 className="text-lg font-semibold tracking-tight">
              Portfolio <span className="text-brand-light">Intelligence</span>
            </h1>
            {meta?.has_data && (
              <span className="text-xs text-slate-300">
                {meta.holdings_count} holdings · base {meta.base_currency} · as of {meta.as_of}
              </span>
            )}
          </div>

          <div className="flex items-center gap-3 print:hidden">
            {dq && !dq.ok && (
              <Pill tone="amber">{dq.count} data issue{dq.count === 1 ? "" : "s"} flagged</Pill>
            )}
            <div className="flex items-center gap-1 rounded-lg bg-white/10 p-1 ring-1 ring-white/10">
              {windows.map((w) => (
                <button
                  key={w}
                  onClick={() => onWindow(w)}
                  className={`rounded-md px-3 py-1 text-sm font-medium transition ${
                    w === window
                      ? "bg-white text-navy shadow-sm"
                      : "text-slate-200 hover:bg-white/10"
                  }`}
                >
                  {WINDOW_LABELS[w]}
                </button>
              ))}
            </div>
            <button
              onClick={() => globalThis.print()}
              className="rounded-md bg-brand px-3 py-1.5 text-sm font-medium text-white shadow-sm transition hover:bg-brand-light"
              title="Export the current view as a PDF (print to PDF)"
            >
              Export PDF
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-6 py-6">{children}</main>

      <footer className="mx-auto max-w-7xl px-6 pb-8 pt-2 text-center text-xs text-slate-400">
        Prototype on mock data · analytics computed server-side ·
        <span className="text-slate-500"> Week 2 of 3 — Build phase</span>
      </footer>
    </div>
  );
}
