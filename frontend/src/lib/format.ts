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

/**
 * Format an ISO 8601 timestamp as a relative duration.
 *
 * Examples:
 *   "just now"
 *   "3 minutes ago"
 *   "2 hours ago"
 *   "yesterday"
 *   "3 days ago"
 *
 * For ages beyond a week, falls back to formatDateTime for an
 * absolute date.
 */
export function formatRelativeTime(
  iso: string | null | undefined
): string {
  if (!iso) return '-'

  try {
    const date = new Date(iso)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffSec = Math.floor(diffMs / 1000)
    const diffMin = Math.floor(diffSec / 60)
    const diffHr = Math.floor(diffMin / 60)
    const diffDay = Math.floor(diffHr / 24)

    if (diffSec < 60) return 'just now'
    if (diffMin < 60) return `${diffMin}m ago`
    if (diffHr < 24) return `${diffHr}h ago`
    if (diffDay === 1) return 'yesterday'
    if (diffDay < 7) return `${diffDay} days ago`

    return formatDateTime(iso)
  } catch {
    return iso
  }
}