import { useEffect, useState } from "react";
import { api } from "./api/client";
import type { Meta, WindowCode } from "./types/api";
import { Shell } from "./components/Shell";
import { SummarySection } from "./sections/SummarySection";
import { ExposureSection } from "./sections/ExposureSection";
import { RiskSection } from "./sections/RiskSection";
import { AttributionSection } from "./sections/AttributionSection";
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
      </div>
    </Shell>
  );
}
