/**
 * WizardShell - shared layout for the template create wizard.
 *
 * Renders a progress stepper at the top and the step's content
 * below. Each step is its own page component with its own URL.
 *
 * Routes:
 *   /templates/new                  -> step 1 (basics)
 *   /templates/new/:id/columns      -> step 2 (columns)
 *   /templates/new/:id/reviewers    -> step 3 (reviewers)
 *   /templates/new/:id/review       -> step 4 (review + submit)
 *
 * The template's ID is in the URL from step 2 onwards because
 * step 1's submit creates the template row.
 */

import { Check } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface WizardStep {
  number: number
  label: string
}

const WIZARD_STEPS: WizardStep[] = [
  { number: 1, label: 'Basics' },
  { number: 2, label: 'Settings' },
  { number: 3, label: 'Columns' },
  { number: 4, label: 'Reviewers' },
  { number: 5, label: 'Review' },
]

interface WizardShellProps {
  currentStep: number
  title: string
  description?: string
  children: React.ReactNode
}

export function WizardShell({
  currentStep,
  title,
  description,
  children,
}: WizardShellProps) {
  return (
    <div className="space-y-8">
      {/* Progress stepper */}
      <div className="flex items-center justify-between max-w-2xl">
        {WIZARD_STEPS.map((step, i) => {
          const isCompleted = step.number < currentStep
          const isActive = step.number === currentStep
          const isLast = i === WIZARD_STEPS.length - 1

          return (
            <div key={step.number} className="flex items-center flex-1">
              <div className="flex flex-col items-center">
                <div
                  className={cn(
                    'w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium',
                    isCompleted && 'bg-green-600 text-white',
                    isActive && 'bg-slate-900 text-white',
                    !isCompleted && !isActive && 'bg-slate-200 text-slate-500'
                  )}
                >
                  {isCompleted ? <Check size={16} /> : step.number}
                </div>
                <div
                  className={cn(
                    'text-xs mt-1',
                    isActive ? 'text-slate-900 font-medium' : 'text-slate-500'
                  )}
                >
                  {step.label}
                </div>
              </div>

              {!isLast && (
                <div
                  className={cn(
                    'flex-1 h-px mx-2 -mt-4',
                    step.number < currentStep ? 'bg-green-600' : 'bg-slate-200'
                  )}
                />
              )}
            </div>
          )
        })}
      </div>

      {/* Step title + description */}
      <div className="space-y-1">
        <h1 className="text-3xl font-bold text-slate-900">{title}</h1>
        {description && (
          <p className="text-slate-600">{description}</p>
        )}
      </div>

      {/* Step body */}
      {children}
    </div>
  )
}