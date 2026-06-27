import { useEffect, useState } from "react";
import { api } from "./api/client";
import type { Meta, WindowCode } from "./types/api";
import { Shell } from "./components/Shell";
import { SummarySection } from "./sections/SummarySection";
import { ExposureSection } from "./sections/ExposureSection";
import { RiskSection } from "./sections/RiskSection";
import { AttributionSection } from "./sections/AttributionSection";
import { AlertsSection } from "./sections/AlertsSection";
import { ScenarioSection } from "./sections/ScenarioSection";
import { ErrorState } from "./components/ui";

export default function App() {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [metaError, setMetaError] = useState<string | null>(null);
  const [window, setWindow] = useState<WindowCode>("YTD");

  useEffect(() => {
    api
      .meta()
      .then((m) => {
        setMeta(m);
        if (m.default_window) setWindow(m.default_window);
      })
      .catch((e) => setMetaError(e.message));
  }, []);

  return (
    <Shell meta={meta} window={window} onWindow={setWindow}>
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
        <SummarySection window={window} />

        {/* Exposure + Risk side by side on wide screens */}
        <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
          <ExposureSection window={window} />
          <RiskSection window={window} />
        </div>

        {/* Attribution full width */}
        <AttributionSection window={window} />

        {/* P1 stretch: alerts (compact) + scenario analysis (wider) */}
        <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
          <div className="xl:col-span-1">
            <AlertsSection window={window} />
          </div>
          <div className="xl:col-span-2">
            <ScenarioSection sectors={meta?.sectors ?? []} isSnapshot={!!meta?.is_snapshot} />
          </div>
        </div>
      </div>
    </Shell>
  );
}
