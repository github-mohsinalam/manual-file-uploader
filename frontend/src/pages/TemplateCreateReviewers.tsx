/**
 * Template Create Wizard - Step 3 (Reviewers).
 *
 * Lets the user configure the approval workflow for this template:
 * which people must approve (required) and who else should be
 * notified (optional).
 *
 * Validation rules:
 *   - At least one required reviewer
 *   - No duplicate emails
 *   - Creator-as-reviewer is enforced by the backend (we display
 *     the 400 response if the user tries it)
 */

import { useEffect, useRef } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Controller, useFieldArray, useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { z } from 'zod'
import { Plus, Trash2 } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Field,
  FieldError,
} from '@/components/ui/field'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

import { WizardShell } from '@/components/wizard/WizardShell'
import { useTemplateReviewers } from '@/hooks/useTemplateReviewers'
import { replaceTemplateReviewers } from '@/services/template-reviewers'
import { toApiError } from '@/lib/api/client'

/** Reviewer type values. Mirrors backend ReviewerType. */
const REVIEWER_TYPES = ['required', 'optional'] as const

/** Validation schema for a single reviewer row. */
const reviewerSchema = z.object({
  reviewer_email: z
    .string()
    .min(1, 'Required')
    .email('Must be a valid email address'),
  reviewer_name: z
    .string()
    .min(1, 'Required')
    .max(100, 'At most 100 characters'),
  reviewer_type: z.enum(REVIEWER_TYPES),
})

/** Validation schema for the full reviewers form. */
const reviewersSchema = z.object({
  reviewers: z
    .array(reviewerSchema)
    .min(1, 'Add at least one reviewer')
    .refine(
      (revs) => revs.some((r) => r.reviewer_type === 'required'),
      { message: 'At least one reviewer must be marked Required' }
    )
    .refine(
      (revs) => {
        const emails = revs.map((r) =>
          r.reviewer_email.trim().toLowerCase()
        )
        return new Set(emails).size === emails.length
      },
      { message: 'Reviewer emails must be unique' }
    ),
})

type ReviewersFormValues = z.infer<typeof reviewersSchema>

/** Default empty reviewer for new rows. */
function emptyReviewer() {
  return {
    reviewer_email: '',
    reviewer_name: '',
    reviewer_type: 'required' as const,
  }
}

export default function TemplateCreateReviewers() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const existingReviewersQuery = useTemplateReviewers(id)

  const form = useForm<ReviewersFormValues>({
    resolver: zodResolver(reviewersSchema),
    defaultValues: {
      reviewers: [emptyReviewer()],
    },
  })

  const { fields, append, remove, replace } = useFieldArray({
    control: form.control,
    name: 'reviewers',
  })

  // Hydrate once if backend returned saved reviewers.
  const hydratedRef = useRef(false)
  useEffect(() => {
    if (hydratedRef.current) return
    if (!existingReviewersQuery.data) return

    if (existingReviewersQuery.data.length > 0) {
      const rows = existingReviewersQuery.data.map((r) => ({
        reviewer_email: r.reviewer_email,
        reviewer_name: r.reviewer_name,
        reviewer_type: r.reviewer_type as (typeof REVIEWER_TYPES)[number],
      }))
      replace(rows)
    }
    hydratedRef.current = true
  }, [existingReviewersQuery.data, replace])

  // Mutation: POST replace-reviewers list.
  const saveMutation = useMutation({
    mutationFn: (reviewers: ReviewersFormValues['reviewers']) =>
      replaceTemplateReviewers(id!, reviewers),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['template-reviewers', id],
      })
      navigate(`/templates/new/${id}/review`)
    },
  })

  function onSubmit(values: ReviewersFormValues) {
    saveMutation.mutate(values.reviewers)
  }

  const saveError = saveMutation.error
    ? toApiError(saveMutation.error)
    : null

  // Pull non-field-level array errors (from .min and .refine).
  const rootError =
    form.formState.errors.reviewers?.root?.message ??
    form.formState.errors.reviewers?.message

  return (
    <WizardShell
      currentStep={3}
      title="Add reviewers"
      description="Configure who must approve this template before it goes live."
    >
      <form
        id="reviewers-form"
        onSubmit={form.handleSubmit(onSubmit)}
      >
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Reviewers ({fields.length})</CardTitle>
                <CardDescription>
                  Required reviewers must all approve before the
                  template is activated. Optional reviewers are
                  notified but do not block approval.
                </CardDescription>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => append(emptyReviewer())}
              >
                <Plus size={14} />
                Add reviewer
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Email</TableHead>
                  <TableHead className="w-48">Name</TableHead>
                  <TableHead className="w-36">Type</TableHead>
                  <TableHead className="w-12"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {fields.map((row, index) => (
                  <ReviewerRow
                    key={row.id}
                    index={index}
                    control={form.control}
                    canRemove={fields.length > 1}
                    onRemove={() => remove(index)}
                  />
                ))}
              </TableBody>
            </Table>

            {rootError && (
              <div className="mt-3 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">
                {rootError}
              </div>
            )}

            {saveError && (
              <div className="mt-3 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">
                {saveError.message}
              </div>
            )}
          </CardContent>
        </Card>
      </form>

      {/* Action buttons */}
      <div className="flex justify-between">
        <Button
          type="button"
          variant="outline"
          onClick={() => navigate(`/templates/new/${id}/columns`)}
          disabled={saveMutation.isPending}
        >
          Back
        </Button>
        <Button
          type="submit"
          form="reviewers-form"
          disabled={saveMutation.isPending}
        >
          {saveMutation.isPending ? 'Saving...' : 'Next: Review'}
        </Button>
      </div>
    </WizardShell>
  )
}

/**
 * One editable row in the reviewers table.
 *
 * Three controllers: email, name, type. The Remove button is
 * disabled when there's only one row left (UX guardrail - users
 * can't accidentally clear the entire list).
 */
function ReviewerRow({
  index,
  control,
  canRemove,
  onRemove,
}: {
  index: number
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  control: any
  canRemove: boolean
  onRemove: () => void
}) {
  return (
    <TableRow>
      {/* Email */}
      <TableCell>
        <Controller
          name={`reviewers.${index}.reviewer_email`}
          control={control}
          render={({ field, fieldState }) => (
            <Field data-invalid={fieldState.invalid}>
              <Input
                {...field}
                type="email"
                aria-invalid={fieldState.invalid}
                placeholder="reviewer@example.com"
                className="h-8"
              />
              {fieldState.invalid && (
                <FieldError errors={[fieldState.error]} />
              )}
            </Field>
          )}
        />
      </TableCell>

      {/* Name */}
      <TableCell>
        <Controller
          name={`reviewers.${index}.reviewer_name`}
          control={control}
          render={({ field, fieldState }) => (
            <Field data-invalid={fieldState.invalid}>
              <Input
                {...field}
                aria-invalid={fieldState.invalid}
                placeholder="Reviewer Name"
                className="h-8"
              />
              {fieldState.invalid && (
                <FieldError errors={[fieldState.error]} />
              )}
            </Field>
          )}
        />
      </TableCell>

      {/* Type */}
      <TableCell>
        <Controller
          name={`reviewers.${index}.reviewer_type`}
          control={control}
          render={({ field }) => (
            <Select value={field.value} onValueChange={field.onChange}>
              <SelectTrigger className="h-8">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {REVIEWER_TYPES.map((t) => (
                  <SelectItem key={t} value={t}>
                    {t}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        />
      </TableCell>

      {/* Remove */}
      <TableCell>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={onRemove}
          disabled={!canRemove}
          className="h-8 w-8 p-0"
        >
          <Trash2 size={14} />
        </Button>
      </TableCell>
    </TableRow>
  )
}