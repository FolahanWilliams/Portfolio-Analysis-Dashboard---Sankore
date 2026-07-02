import { useEffect, useState } from "react";
import { api } from "./api/client";
import type { Meta, WindowCode } from "./types/api";
import { Shell } from "./components/Shell";
import { SummarySection } from "./sections/SummarySection";
import { HoldingsSection } from "./sections/HoldingsSection";
import { ExposureSection } from "./sections/ExposureSection";
import { RiskSection } from "./sections/RiskSection";
import { AttributionSection } from "./sections/AttributionSection";
import { AlertsSection } from "./sections/AlertsSection";
import { ScenarioSection } from "./sections/ScenarioSection";
import { ChatWidget } from "./components/ChatWidget";
import { ErrorState } from "./components/ui";

export default function App() {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [metaError, setMetaError] = useState<string | null>(null);
  const [window, setWindow] = useState<WindowCode>("YTD");
  // Live-price refresh. `live` flips on the first press and stays on; each press
  // bumps `refreshTick` so every panel re-fetches even when live is already on.
  const [live, setLive] = useState(false);
  const [refreshTick, setRefreshTick] = useState(0);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    let alive = true;
    api
      .meta(live)
      .then((m) => {
        if (!alive) return;
        setMeta(m);
        if (refreshTick === 0 && m.default_window) setWindow(m.default_window);
      })
      .catch((e) => alive && setMetaError(e.message))
      .finally(() => alive && setRefreshing(false));
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshTick]);

  const handleRefresh = () => {
    setLive(true);
    setRefreshing(true);
    setRefreshTick((t) => t + 1);
  };

  return (
    <Shell
      meta={meta}
      window={window}
      onWindow={setWindow}
      onRefresh={handleRefresh}
      refreshing={refreshing}
      live={live}
    >
      {metaError && (
        <div className="mb-6">
          <ErrorState message={`${metaError}. Start the backend with: cd backend && uvicorn app.main:app --reload`} />
        </div>
      )}

      {meta?.provenance && (
        <div className="mb-6 flex items-start gap-3 rounded-lg border border-brand/20 bg-blue-50/60 px-4 py-3">
          <span className="mt-0.5 inline-block h-2 w-2 shrink-0 rounded-full bg-brand" />
          <p className="text-sm text-slate-600">
            <span className="font-semibold text-navy">Static snapshot.</span> {meta.provenance}
          </p>
        </div>
      )}

      <div className="space-y-6">
        {/* Portfolio Summary spans the top -- the three core answers, no scroll */}
        <SummarySection window={window} live={live} refreshTick={refreshTick} />

        {/* What we own: bought price vs current price and P&L, per stock */}
        <HoldingsSection window={window} live={live} refreshTick={refreshTick} />

        {/* Sector & geographic exposure -- full width, its own panel */}
        <ExposureSection window={window} live={live} refreshTick={refreshTick} />

        {/* Performance attribution sits directly under exposure */}
        <AttributionSection window={window} live={live} refreshTick={refreshTick} />

        {/* Risk metrics moved down, full width */}
        <RiskSection window={window} live={live} refreshTick={refreshTick} />

        {/* P1 stretch: alerts (compact) + scenario analysis (wider) */}
        <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
          <div className="xl:col-span-1">
            <AlertsSection window={window} live={live} refreshTick={refreshTick} />
          </div>
          <div className="xl:col-span-2">
            <ScenarioSection
              sectors={meta?.sectors ?? []}
              isSnapshot={!!meta?.is_snapshot}
              live={live}
              refreshTick={refreshTick}
            />
          </div>
        </div>
      </div>
      <ChatWidget />
    </Shell>
  );
}
