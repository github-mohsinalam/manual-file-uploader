/**
 * Configured axios instance for talking to the FastAPI backend.
 *
 * All API calls in the application go through this client.
 * Centralizing here means we have one place to:
 *   - Set the base URL
 *   - Add auth headers when Phase 8 (Entra ID) lands
 *   - Add request/response logging
 *   - Handle global error transformations
 */

import axios, { type AxiosInstance, AxiosError } from 'axios'

/**
 * Base URL of the FastAPI server.
 *
 * Read from VITE_API_BASE_URL at build time. Vite inlines the
 * value when bundling, so the running browser code sees the
 * literal URL string — never the env-var read.
 *
 * `import.meta.env` is the Vite convention for accessing env
 * variables in the frontend .
 */
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

/**
 * The shared axios instance used everywhere in the app.
 *
 * Components do NOT import axios directly. They import this
 * client instead. This way, changes to defaults (auth headers,
 * timeouts, etc.) only need to happen in one place.
 */
export const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  // 30 seconds. File uploads have their own longer timeout
  // configured per-request in Task 9.15.
  timeout: 30_000,
  headers: {
    'Content-Type': 'application/json',
  },
})

/**
 * Standardized error shape for the rest of the app to consume.
 *
 * Components don't have to know about axios's AxiosError type.
 * They get a plain object with the fields they need.
 */
export interface ApiError {
  /** HTTP status code (0 if the request never made it out) */
  status: number
  /** Human-readable message extracted from the response */
  message: string
  /** Original error for debugging if needed */
  original: unknown
}

/**
 * Convert any error thrown by axios into our ApiError shape.
 *
 * FastAPI returns errors in two common shapes:
 *   { "detail": "Template not found" }            (HTTPException)
 *   { "detail": [{ "loc": [...], "msg": "..." }]} (validation error)
 *
 * We extract the most useful string we can find.
 */
export function toApiError(err: unknown): ApiError {
  if (axios.isAxiosError(err)) {
    const axiosErr = err as AxiosError<{ detail?: unknown }>
    const status = axiosErr.response?.status ?? 0
    const detail = axiosErr.response?.data?.detail

    let message: string
    if (typeof detail === 'string') {
      message = detail
    } else if (Array.isArray(detail) && detail.length > 0) {
      // Validation error array - take the first message
      const first = detail[0] as { msg?: string }
      message = first.msg ?? 'Validation failed'
    } else {
      message = axiosErr.message || 'Request failed'
    }

    return { status, message, original: err }
  }

  // Not an axios error - shouldn't happen in practice but
  // we guard against it to keep types honest.
  return {
    status: 0,
    message: err instanceof Error ? err.message : 'Unknown error',
    original: err,
  }
}