/**
 * Template Create Wizard - Step 4 (Review + Submit).
 *
 * Placeholder for Task 9.13.
 */

import { useParams, useNavigate } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { WizardShell } from '@/components/wizard/WizardShell'

export default function TemplateCreateReview() {
  const { id } = useParams()
  const navigate = useNavigate()

  return (
    <WizardShell
      currentStep={4}
      title="Review and submit"
      description="Confirm everything looks correct, then submit for approval."
    >
      <Card>
        <CardContent className="pt-6 space-y-4">
          <p className="text-slate-600">
            Review step lands in Task 9.13. For now this confirms
            the wizard flow.
          </p>
          <p className="text-sm">
            Template ID:{' '}
            <code className="bg-slate-100 px-1 py-0.5 rounded">{id}</code>
          </p>
          <div className="flex justify-between pt-2">
            <Button
              variant="outline"
              onClick={() => navigate(`/templates/new/${id}/reviewers`)}
            >
              Back to reviewers
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