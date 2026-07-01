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
  onRefresh,
  refreshing = false,
  live = false,
  children,
}: {
  meta: Meta | null;
  window: WindowCode;
  onWindow: (w: WindowCode) => void;
  onRefresh?: () => void;
  refreshing?: boolean;
  live?: boolean;
  children: ReactNode;
}) {
  const windows = meta?.windows ?? (["MTD", "QTD", "YTD", "1Y", "ALL"] as WindowCode[]);
  const dq = meta?.data_quality;
  const liveInfo = meta?.live ?? null;
  // The refreshed-at time is a wall clock (e.g. 2026-07-01T11:52:02); show HH:MM.
  const refreshedClock = liveInfo?.refreshed_at ? liveInfo.refreshed_at.slice(11, 16) : null;
  const liveThrottled = live && liveInfo && liveInfo.ok === false;

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
                {meta.holdings_count} holdings · base {meta.base_currency}
                {meta.benchmark ? ` · vs ${meta.benchmark}` : ""} · as of {meta.as_of}
                {meta.price_source && meta.price_source !== "snapshot" ? ` · prices: ${meta.price_source}` : ""}
                {live && liveInfo?.ok && refreshedClock ? (
                  <span className="ml-1 text-emerald-300">· live · refreshed {refreshedClock}</span>
                ) : null}
              </span>
            )}
          </div>

          <div className="flex items-center gap-3 print:hidden">
            {liveThrottled && (
              <Pill tone="amber" title={liveInfo?.error}>Live prices unavailable — showing last committed</Pill>
            )}
            {dq && !dq.ok && (
              <Pill tone="amber">{dq.count} data issue{dq.count === 1 ? "" : "s"} flagged</Pill>
            )}
            {meta?.is_snapshot ? (
              <span className="rounded-md bg-white/10 px-3 py-1 text-xs font-medium text-slate-200 ring-1 ring-white/10">
                Snapshot · {meta.as_of}
              </span>
            ) : (
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
            )}
            {!meta?.is_snapshot && onRefresh && (
              <button
                onClick={onRefresh}
                disabled={refreshing}
                className="flex items-center gap-1.5 rounded-md bg-white/10 px-3 py-1.5 text-sm font-medium text-white shadow-sm ring-1 ring-white/15 transition hover:bg-white/20 disabled:cursor-wait disabled:opacity-70"
                title="Pull the latest prices from Yahoo Finance and recompute every panel"
              >
                <svg
                  viewBox="0 0 24 24"
                  className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`}
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M21 12a9 9 0 1 1-2.64-6.36" />
                  <path d="M21 3v6h-6" />
                </svg>
                {refreshing ? "Refreshing…" : "Refresh prices"}
              </button>
            )}
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
