import { useEffect, useRef, useState } from "react"
import { ApiError, getElements, getRun, type Element, type RunStatus } from "./api"

const POLL_INTERVAL_MS = 1500
const POLLING_STATES = new Set(["PENDING", "BREAKDOWN"])

export interface UseRunResult {
  status: RunStatus | null
  elements: Element[] | null
  error: ApiError | Error | null
  loading: boolean
}

/**
 * Polls GET /api/runs/{id} every 1500ms while the run is PENDING/BREAKDOWN.
 * Stops polling once the run reaches AWAITING_START, FAILED, or any later
 * state. Fetches the element inventory exactly once, when the run first
 * reaches AWAITING_START.
 */
export function useRun(runId: string | null): UseRunResult {
  const [status, setStatus] = useState<RunStatus | null>(null)
  const [elements, setElements] = useState<Element[] | null>(null)
  const [error, setError] = useState<ApiError | Error | null>(null)
  const [loading, setLoading] = useState(false)

  // Tracks whether we've already fetched elements for the current runId,
  // so AWAITING_START polls (if any ever happen) don't refetch.
  const fetchedElementsFor = useRef<string | null>(null)

  useEffect(() => {
    setStatus(null)
    setElements(null)
    setError(null)
    fetchedElementsFor.current = null

    if (!runId) {
      setLoading(false)
      return
    }

    let cancelled = false
    let timer: ReturnType<typeof setTimeout> | null = null
    setLoading(true)

    async function fetchElementsOnce(id: string) {
      if (fetchedElementsFor.current === id) return
      fetchedElementsFor.current = id
      try {
        const list = await getElements(id)
        if (!cancelled) setElements(list.elements)
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err : new Error(String(err)))
      }
    }

    async function poll() {
      try {
        const next = await getRun(runId as string)
        if (cancelled) return
        setStatus(next)
        setLoading(false)

        if (next.state === "AWAITING_START") {
          await fetchElementsOnce(runId as string)
        }

        if (POLLING_STATES.has(next.state)) {
          timer = setTimeout(poll, POLL_INTERVAL_MS)
        }
      } catch (err) {
        if (cancelled) return
        setError(err instanceof Error ? err : new Error(String(err)))
        setLoading(false)
      }
    }

    poll()

    return () => {
      cancelled = true
      if (timer) clearTimeout(timer)
    }
  }, [runId])

  return { status, elements, error, loading }
}
