/**
 * StatusBadge - small colored chip showing a template status.
 *
 * Used across the templates list, detail page, and approval
 * page. Colors are derived from getStatusStyle so the entire
 * app stays consistent.
 */

import { Badge } from '@/components/ui/badge'
import { getStatusStyle } from '@/lib/template-status'
import { cn } from '@/lib/utils'
import type { TemplateStatus } from '@/types'

interface StatusBadgeProps {
  status: TemplateStatus
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const style = getStatusStyle(status)
  return (
    <Badge variant="outline" className={cn(style.className)}>
      {style.label}
    </Badge>
  )
}