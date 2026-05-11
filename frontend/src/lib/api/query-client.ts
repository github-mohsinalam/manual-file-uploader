/**
 * The TanStack QueryClient configured for this application.
 *
 * One instance is created here and shared across the whole app
 * via QueryClientProvider in main.tsx. Every useQuery and
 * useMutation hook in the application reads from / writes to
 * this client's cache.
 */

import { QueryClient } from '@tanstack/react-query'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // How long fetched data is considered fresh. While "fresh",
      // re-renders or window-focus events do NOT trigger a refetch.
      // 30 seconds is a sensible default for most resources.
      staleTime: 30_000,

      // Retry failed queries 1 time. Default is 3 which can be
      // noisy in development. Production may want higher.
      retry: 1,

      // Don't refetch automatically when the user focuses the
      // browser tab again. Personal preference - it's a common
      // source of "why is my data flickering" surprises for
      // people new to React Query.
      refetchOnWindowFocus: false,
    },
    mutations: {
      // Don't auto-retry mutations - they're not idempotent
      // by default and a duplicate POST is worse than a 500.
      retry: 0,
    },
  },
})