/**
 * UploadStatusBadge - small colored chip showing upload status.
 *
 * Used in the uploads list and the progress page. Colors come
 * from getUploadStatusStyle for consistency.
 */

import { Badge } from '@/components/ui/badge'
import { getUploadStatusStyle } from '@/lib/upload-status'
import { cn } from '@/lib/utils'
import type { UploadStatus } from '@/types'

interface UploadStatusBadgeProps {
  status: UploadStatus
}

export function UploadStatusBadge({ status }: UploadStatusBadgeProps) {
  const style = getUploadStatusStyle(status)
  return (
    <Badge variant="outline" className={cn(style.className)}>
      {style.label}
    </Badge>
  )
}