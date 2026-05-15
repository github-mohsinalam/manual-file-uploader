/**
 * Template Create Wizard - Step 3 (Reviewers).
 *
 * Placeholder for Task 9.12.
 */

import { useParams, useNavigate } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { WizardShell } from '@/components/wizard/WizardShell'

export default function TemplateCreateReviewers() {
  const { id } = useParams()
  const navigate = useNavigate()

  return (
    <WizardShell
      currentStep={3}
      title="Add reviewers"
      description="Configure who must approve this template."
    >
      <Card>
        <CardContent className="pt-6 space-y-4">
          <p className="text-slate-600">
            Reviewers step lands in Task 9.12.
          </p>
          <p className="text-sm">
            Template ID:{' '}
            <code className="bg-slate-100 px-1 py-0.5 rounded">{id}</code>
          </p>
          <div className="flex justify-between pt-2">
            <Button
              variant="outline"
              onClick={() => navigate(`/templates/new/${id}/columns`)}
            >
              Back to columns
            </Button>
            <Button onClick={() => navigate(`/templates/${id}`)}>
              View Template
            </Button>
          </div>
        </CardContent>
      </Card>
    </WizardShell>
  )
}