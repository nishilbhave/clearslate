import type { RunStatus } from "../api"

interface RunProgressProps {
  status: RunStatus
}

const STATE_LABELS: Record<string, string> = {
  PENDING: "Queued",
  BREAKDOWN: "Breaking down",
  AWAITING_START: "Ready",
  RESEARCH: "Researching",
  GRADING: "Grading",
  REPORT: "Reporting",
  DONE: "Done",
  FAILED: "Failed",
}

/** Shows run state + a breakdown-in-progress spinner, or a FAILED banner. */
export function RunProgress({ status }: RunProgressProps) {
  const isBreaking = status.state === "PENDING" || status.state === "BREAKDOWN"

  return (
    <div className="run-progress">
      <span className={`state-badge state-badge--${status.state.toLowerCase()}`}>
        {STATE_LABELS[status.state] ?? status.state}
      </span>

      {isBreaking && (
        <div className="run-progress__spinner-row">
          <span className="spinner" aria-hidden="true" />
          <span>Breaking down {status.page_count} pages…</span>
        </div>
      )}

      {status.state === "FAILED" && (
        <div className="error-banner" role="alert">
          <span className="error-banner__code">run_failed</span>
          <span className="error-banner__message">
            {status.error ?? "The run failed for an unknown reason."}
          </span>
        </div>
      )}
    </div>
  )
}
