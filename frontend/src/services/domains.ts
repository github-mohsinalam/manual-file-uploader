/**
 * Domain API service.
 *
 * Service functions wrap the API client with typed, named methods.
 * Components call these instead of touching axios directly.
 *
 * This indirection pays off when:
 *   - URL paths change (one place to update)
 *   - We need to massage response data
 *   - We need to add request-level logic (caching headers, etc.)
 */

import { api } from '@/lib/api/client'
import type { Domain } from '@/types'

/**
 * Fetch all domains from the backend.
 *
 * Backend endpoint: GET /api/v1/domains
 * Returns the seeded list of business domains.
 */
export async function listDomains(): Promise<Domain[]> {
  const response = await api.get<Domain[]>('/api/v1/domains')
  return response.data
}