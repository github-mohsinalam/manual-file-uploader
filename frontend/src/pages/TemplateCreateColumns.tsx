/**
 * Template Create Wizard - Step 2 (Columns).
 *
 * Placeholder for Task 9.11. For now this just confirms:
 *   - The redirect from step 1 worked
 *   - The new template's ID arrived via the URL
 */

import { useParams, useNavigate } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { WizardShell } from '@/components/wizard/WizardShell'

export default function TemplateCreateColumns() {
  const { id } = useParams()
  const navigate = useNavigate()

  return (
    <WizardShell
      currentStep={2}
      title="Configure columns"
      description="Define the column structure of the target table."
    >
      <Card>
        <CardContent className="pt-6 space-y-4">
          <p className="text-slate-600">
            Columns step lands in Task 9.11. For now this placeholder
            confirms the wizard flow and the template ID from the URL.
          </p>
          <p className="text-sm">
            Template ID from URL:{' '}
            <code className="bg-slate-100 px-1 py-0.5 rounded">
              {id}
            </code>
          </p>
          <div className="flex justify-between pt-2">
            <Button
              variant="outline"
              onClick={() => navigate(`/templates/${id}`)}
            >
              View Template
            </Button>
            <Button onClick={() => navigate('/templates')}>
              Back to Templates List
            </Button>
          </div>
        </CardContent>
      </Card>
    </WizardShell>
  )
}