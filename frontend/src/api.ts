// TS mirrors of the ClearSlate wire types. Keep these in exact sync with
// clearslate/models.py and clearslate/api/schemas.py.

export type ElementCategory =
  | "character_name"
  | "business_org"
  | "location_address"
  | "phone_url_email"
  | "product_brand"
  | "referenced_work"
  | "real_person"
  | "on_screen_text"
  | "vehicle_identifier"

export type RunState =
  | "PENDING"
  | "BREAKDOWN"
  | "AWAITING_START"
  | "RESEARCH"
  | "GRADING"
  | "REPORT"
  | "DONE"
  | "FAILED"

export interface CostEstimate {
  element_count: number
  search_requests: number
  task_runs: number
  gemini_usd: number
  parallel_usd: number
  total_usd: number
  basis: "pages" | "elements"
}

export interface Element {
  id: string
  category: ElementCategory
  text: string
  normalized_text: string
  pages: number[]
  scene: string | null
  context_snippet: string
  status: string
  findings: unknown[]
  grade: string | null
  rule_citation: string | null
  alternatives: unknown[]
}

export interface RunCreated {
  run_id: string
  state: RunState
  page_count: number
  element_estimate: number
  cost_estimate: CostEstimate
}

export interface RunStatus {
  run_id: string
  state: RunState
  page_count: number
  element_count: number | null
  counts_by_category: Record<string, number> | null
  cost_estimate: CostEstimate | null
  error: string | null
}

export interface ElementList {
  run_id: string
  elements: Element[]
}

/** Typed error thrown for non-2xx API responses. */
export class ApiError extends Error {
  code: string
  status: number

  constructor(code: string, message: string, status: number) {
    super(message)
    this.name = "ApiError"
    this.code = code
    this.status = status
  }
}

async function parseErrorDetail(res: Response): Promise<{ code: string; message: string }> {
  try {
    const body = await res.json()
    const detail = body?.detail
    if (detail && typeof detail === "object" && "code" in detail && "message" in detail) {
      return { code: String(detail.code), message: String(detail.message) }
    }
    if (typeof detail === "string") {
      return { code: "error", message: detail }
    }
  } catch {
    // fall through to generic error below
  }
  return { code: "unknown_error", message: `Request failed with status ${res.status}.` }
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const { code, message } = await parseErrorDetail(res)
    throw new ApiError(code, message, res.status)
  }
  return (await res.json()) as T
}

export async function createRun(input: { file?: File; text?: string }): Promise<RunCreated> {
  const form = new FormData()
  if (input.file) form.append("file", input.file)
  if (input.text) form.append("text", input.text)

  const res = await fetch("/api/runs", { method: "POST", body: form })
  return handleResponse<RunCreated>(res)
}

export async function getRun(runId: string): Promise<RunStatus> {
  const res = await fetch(`/api/runs/${runId}`)
  return handleResponse<RunStatus>(res)
}

export async function getElements(runId: string): Promise<ElementList> {
  const res = await fetch(`/api/runs/${runId}/elements`)
  return handleResponse<ElementList>(res)
}
