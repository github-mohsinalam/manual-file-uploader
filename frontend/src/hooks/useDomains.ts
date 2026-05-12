/**
 * useDomains - custom hook for fetching the list of domains.
 *
 * Wraps useQuery so any component that needs domains gets the
 * same cached result. Calling useDomains() multiple times in
 * different components only fires one network request - TanStack
 * Query deduplicates queries with the same queryKey.
 */

import { useQuery } from '@tanstack/react-query'
import { listDomains } from '@/services/domains'
import type { Domain } from '@/types'

export function useDomains() {
  return useQuery<Domain[]>({
    queryKey: ['domains'],
    queryFn: listDomains,
  })
}