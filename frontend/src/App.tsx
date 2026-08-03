import { useMemo, useState } from "react"
import type { RunCreated } from "./api"
import { countByCategory } from "./categories"
import { CategoryFilterBar } from "./components/CategoryFilterBar"
import { CostEstimateCard } from "./components/CostEstimateCard"
import { InventoryTable } from "./components/InventoryTable"
import { RunProgress } from "./components/RunProgress"
import { UploadPane } from "./components/UploadPane"
import { useRun } from "./useRun"

function App() {
  const [runId, setRunId] = useState<string | null>(null)
  const [runCreated, setRunCreated] = useState<RunCreated | null>(null)
  const [activeFilter, setActiveFilter] = useState<string | null>(null)

  const { status, elements, error } = useRun(runId)

  const counts = useMemo(() => countByCategory(elements ?? []), [elements])

  function handleCreated(run: RunCreated) {
    setRunCreated(run)
    setActiveFilter(null)
    setRunId(run.run_id)
  }

  function handleReset() {
    setRunId(null)
    setRunCreated(null)
    setActiveFilter(null)
  }

  const isAwaitingStart = status?.state === "AWAITING_START"
  // Prefer the live status once polling starts returning data; fall back to
  // the immediate RunCreated response so the cost card never blanks out.
  const preStartEstimate = status?.cost_estimate ?? runCreated?.cost_estimate ?? null

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-header__titles">
          <h1>
            ClearSlate <span className="app-header__dash">—</span> Script Pre-Clearance
          </h1>
          <p className="app-header__tagline">
            Every name checked against the real world. In minutes.
          </p>
        </div>
        {runId && (
          <button type="button" className="button button--ghost" onClick={handleReset}>
            Start over
          </button>
        )}
      </header>

      <main className="app-main">
        {!runId && <UploadPane onCreated={handleCreated} />}

        {runId && !isAwaitingStart && status?.state !== "FAILED" && (
          <div className="run-view">
            {preStartEstimate && <CostEstimateCard estimate={preStartEstimate} />}
            {status ? (
              <RunProgress status={status} />
            ) : (
              <div className="run-progress">
                <div className="run-progress__spinner-row">
                  <span className="spinner" aria-hidden="true" />
                  <span>Starting…</span>
                </div>
              </div>
            )}
          </div>
        )}

        {runId && status?.state === "FAILED" && <RunProgress status={status} />}

        {runId && isAwaitingStart && status && (
          <div className="run-view">
            {status.cost_estimate && <CostEstimateCard estimate={status.cost_estimate} />}
            <CategoryFilterBar counts={counts} active={activeFilter} onChange={setActiveFilter} />
            <InventoryTable elements={elements ?? []} filter={activeFilter} />
          </div>
        )}

        {error && (
          <div className="error-banner" role="alert">
            <span className="error-banner__code">connection_error</span>
            <span className="error-banner__message">{error.message}</span>
          </div>
        )}
      </main>
    </div>
  )
}

export default App
