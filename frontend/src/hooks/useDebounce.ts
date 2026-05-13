/**
 * useDebounce - delays propagating a value change until it has
 * been stable for the given duration.
 *
 * Typical use: a search input. Re-render the input every
 * keystroke (fast UX), but only re-fetch from the server when
 * the user has stopped typing for 300ms.
 *
 *   const [search, setSearch] = useState('')
 *   const debouncedSearch = useDebounce(search, 300)
 *   // The query uses debouncedSearch, not search
 */

import { useEffect, useState } from 'react'

export function useDebounce<T>(value: T, delayMs: number): T {
  const [debouncedValue, setDebouncedValue] = useState(value)

  useEffect(() => {
    // Schedule an update for `delayMs` from now.
    const timer = setTimeout(() => {
      setDebouncedValue(value)
    }, delayMs)

    // If `value` changes again before the timer fires, this
    // cleanup cancels the pending update. Then a new timer is
    // scheduled by the next effect run. The effect's
    // self-cancellation is what makes the debouncing work.
    return () => clearTimeout(timer)
  }, [value, delayMs])

  return debouncedValue
}