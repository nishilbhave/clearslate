import type { CostEstimate } from "../api"

interface CostEstimateCardProps {
  estimate: CostEstimate
}

function formatUsd(value: number): string {
  const decimals = value < 0.01 && value > 0 ? 4 : 2
  return `$${value.toFixed(decimals)}`
}

const BASIS_CAPTION: Record<CostEstimate["basis"], string> = {
  pages: "Estimated from page count — refines once elements are extracted.",
  elements: "Based on the extracted element inventory.",
}

/** Compact cost/usage summary card, used both pre- and post-breakdown. */
export function CostEstimateCard({ estimate }: CostEstimateCardProps) {
  return (
    <div className="cost-card">
      <div className="cost-card__total">
        <span className="cost-card__total-value">{formatUsd(estimate.total_usd)}</span>
        <span className="cost-card__total-label">estimated cost</span>
      </div>
      <dl className="cost-card__stats">
        <div className="cost-card__stat">
          <dt>Elements</dt>
          <dd>{estimate.element_count}</dd>
        </div>
        <div className="cost-card__stat">
          <dt>Search requests</dt>
          <dd>{estimate.search_requests}</dd>
        </div>
        <div className="cost-card__stat">
          <dt>Task runs</dt>
          <dd>{estimate.task_runs}</dd>
        </div>
        <div className="cost-card__stat">
          <dt>Gemini</dt>
          <dd>{formatUsd(estimate.gemini_usd)}</dd>
        </div>
        <div className="cost-card__stat">
          <dt>Parallel</dt>
          <dd>{formatUsd(estimate.parallel_usd)}</dd>
        </div>
      </dl>
      <p className="cost-card__caption">{BASIS_CAPTION[estimate.basis]}</p>
    </div>
  )
}
