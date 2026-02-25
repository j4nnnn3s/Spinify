import { useCallback, useEffect, useRef } from 'react'

/** Adaptive polling: faster when active (playing), slower when idle. */
export function usePolling(
  fn: () => Promise<void>,
  options: {
    /** Interval in ms when "active" (e.g. playing). */
    activeIntervalMs?: number
    /** Interval in ms when idle. */
    idleIntervalMs?: number
    /** Whether we consider the state "active" right now. */
    isActive?: boolean
    /** Run immediately on mount. */
    runOnMount?: boolean
  } = {}
) {
  const {
    activeIntervalMs = 2000,
    idleIntervalMs = 5000,
    isActive = false,
    runOnMount = true,
  } = options

  const fnRef = useRef(fn)
  fnRef.current = fn
  const run = useCallback(() => fnRef.current(), [])

  useEffect(() => {
    if (runOnMount) run()
    const intervalMs = isActive ? activeIntervalMs : idleIntervalMs
    const t = setInterval(run, intervalMs)
    return () => clearInterval(t)
  }, [runOnMount, run, isActive, activeIntervalMs, idleIntervalMs])
}
