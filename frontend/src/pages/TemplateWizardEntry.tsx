/**
 * Template Wizard Entry - router for resuming the wizard.
 *
 * Hit when the user clicks Edit on a Draft template, or via a
 * URL like /templates/new/<id>. We don't have a UI of our own -
 * we just redirect to the correct wizard step:
 *
 *   - No columns saved          -> Step 2 (columns)
 *   - Columns saved, no reviewers -> Step 3 (reviewers)
 *   - Both saved                -> Step 4 (review)
 *
 * While the two queries are in flight, we show a brief loading
 * placeholder. Once both resolve, useEffect fires and navigate()
 * redirects.
 */

import { useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Loader2 } from 'lucide-react'

import { useTemplateColumns } from '@/hooks/useTemplateColumns'
import { useTemplateReviewers } from '@/hooks/useTemplateReviewers'

export default function TemplateWizardEntry() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const columnsQuery = useTemplateColumns(id)
  const reviewersQuery = useTemplateReviewers(id)

  useEffect(() => {
    // Wait for both queries to resolve.
    if (columnsQuery.isLoading || reviewersQuery.isLoading) return
    if (!id) return

    const hasColumns = (columnsQuery.data?.length ?? 0) > 0
    const hasReviewers = (reviewersQuery.data?.length ?? 0) > 0

    let target: string
    if (hasColumns && hasReviewers) {
      target = `/templates/new/${id}/review`
    } else if (hasColumns) {
      target = `/templates/new/${id}/reviewers`
    } else {
      target = `/templates/new/${id}/columns`
    }

    // replace: true so the entry URL doesn't add a useless
    // history entry. Back from the target step should go to
    // wherever the user came from (e.g. the detail page).
    navigate(target, { replace: true })
  }, [
    id,
    columnsQuery.isLoading,
    columnsQuery.data,
    reviewersQuery.isLoading,
    reviewersQuery.data,
    navigate,
  ])

  return (
    <div className="flex items-center justify-center py-20">
      <div className="flex items-center gap-2 text-slate-500 text-sm">
        <Loader2 className="animate-spin" size={16} />
        Loading wizard...
      </div>
    </div>
  )
}