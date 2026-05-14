/**
 * Small formatting helpers shared across pages.
 *
 * Using Intl.DateTimeFormat directly - no date library needed.
 */

/**
 * Format an ISO 8601 timestamp string as a readable absolute
 * date and time. Example: "May 10, 2026 at 8:25 AM".
 *
 * Returns "-" for null/undefined input so callers can render
 * the result unconditionally.
 */
export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '-'
  try {
    const date = new Date(iso)
    return new Intl.DateTimeFormat('en-US', {
      dateStyle: 'medium',
      timeStyle: 'short',
    }).format(date)
  } catch {
    return iso
  }
}