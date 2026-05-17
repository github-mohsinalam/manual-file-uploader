/**
 * Template Create Wizard - Step 2 (Settings).
 *
 * Captures advanced fields that have sensible defaults at create
 * time but are commonly tuned:
 *   - File handling: file_format, delimiter, encoding
 *   - Write behavior: write_mode, reader_group
 *   - Validation: bad_row_threshold, bad_row_action
 *
 * Save uses PATCH /templates/{id} - the template row already
 * exists from Step 1. Fields not changed by the user are sent
 * anyway; the backend uses exclude_unset semantics so it's a
 * no-op for unchanged data on the wire (we send all fields
 * because rhf doesn't track per-field dirty state cleanly with
 * Controller; this is a trade-off for code simplicity).
 *
 * Validation rules mirror the SQL CHECK constraints:
 *   - file_format IN ('csv', 'xlsx')
 *   - write_mode IN ('append', 'overwrite')
 *   - bad_row_action IN ('fail', 'drop')
 *   - bad_row_threshold BETWEEN 0 AND 100
 */

import { useEffect, useRef } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Controller, useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { z } from 'zod'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Field,
  FieldDescription,
  FieldError,
  FieldGroup,
  FieldLabel,
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
import { Skeleton } from '@/components/ui/skeleton'

import { WizardShell } from '@/components/wizard/WizardShell'
import { useTemplate } from '@/hooks/useTemplate'
import { updateTemplate } from '@/services/templates'
import { toApiError } from '@/lib/api/client'

/**
 * Validation schema. Mirrors backend TemplateUpdate + the SQL
 * CHECK constraints on the templates table.
 */
const settingsSchema = z.object({
  file_format: z.enum(['csv', 'xlsx']),
  delimiter: z
    .string()
    .min(1, 'Required')
    .max(5, 'At most 5 characters'),
  encoding: z
    .string()
    .min(1, 'Required')
    .max(20, 'At most 20 characters'),

  write_mode: z.enum(['append', 'overwrite']),
  reader_group: z
    .string()
    .max(255, 'At most 255 characters')
    .optional(),

  bad_row_threshold: z
    .number({ message: 'Must be a number' })
    .min(0, 'Must be 0 or more')
    .max(100, 'Must be 100 or less'),
  bad_row_action: z.enum(['fail', 'drop']),
})

type SettingsFormValues = z.infer<typeof settingsSchema>

/** Default values used when no template loaded yet. */
const FALLBACK_DEFAULTS: SettingsFormValues = {
  file_format: 'csv',
  delimiter: ',',
  encoding: 'UTF-8',
  write_mode: 'append',
  reader_group: '',
  bad_row_threshold: 5,
  bad_row_action: 'fail',
}

export default function TemplateCreateSettings() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  // Fetch the template so we can hydrate the form with existing
  // values (template was created in Step 1 with defaults; user
  // may also be revisiting after partial setup).
  const templateQuery = useTemplate(id)

  const form = useForm<SettingsFormValues>({
    resolver: zodResolver(settingsSchema),
    defaultValues: FALLBACK_DEFAULTS,
  })

  // Hydrate once when template data arrives. ref-guarded so the
  // user's in-progress edits aren't clobbered if the query
  // refetches.
  const hydratedRef = useRef(false)
  useEffect(() => {
    if (hydratedRef.current) return
    if (!templateQuery.data) return

    const t = templateQuery.data
    form.reset({
      file_format: (t.file_format as 'csv' | 'xlsx') ?? 'csv',
      delimiter: t.delimiter ?? ',',
      encoding: t.encoding ?? 'UTF-8',
      write_mode: (t.write_mode as 'append' | 'overwrite') ?? 'overwrite',
      reader_group: t.reader_group ?? '',
      // bad_row_threshold comes back as string or Decimal from JSON,
      // ensure it's coerced to a number for the form.
      bad_row_threshold: Number(t.bad_row_threshold ?? 5),
      bad_row_action: (t.bad_row_action as 'fail' | 'drop') ?? 'fail',
    })
    hydratedRef.current = true
  }, [templateQuery.data, form])

  const saveMutation = useMutation({
    mutationFn: (values: SettingsFormValues) =>
      updateTemplate(id!, {
        ...values,
        // bad_row_threshold is typed as string in TemplateUpdate
        // (backend stores as Decimal, serializes as string in JSON
        // to preserve precision). Our form holds it as number;
        // convert here.
        bad_row_threshold: values.bad_row_threshold.toString(),
        // Backend treats empty string as "set field to empty"
        // (not null). Send null when user clears reader_group.
        reader_group: values.reader_group?.trim()
          ? values.reader_group
          : null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['template', id] })
      navigate(`/templates/new/${id}/columns`)
    },
  })

  function onSubmit(values: SettingsFormValues) {
    saveMutation.mutate(values)
  }

  const apiError = saveMutation.error
    ? toApiError(saveMutation.error)
    : null

  if (templateQuery.isLoading || !templateQuery.data) {
    return (
      <WizardShell
        currentStep={2}
        title="Settings"
        description="Configure file handling, write behavior, and validation."
      >
        <Skeleton className="h-64 w-full" />
      </WizardShell>
    )
  }

  return (
    <WizardShell
      currentStep={2}
      title="Settings"
      description="Configure file handling, write behavior, and validation. Defaults are sensible - adjust only if you have specific requirements."
    >
      <form
        id="template-settings-form"
        onSubmit={form.handleSubmit(onSubmit)}
        className="space-y-6"
      >
        {/* File handling */}
        <Card>
          <CardHeader>
            <CardTitle>File handling</CardTitle>
            <CardDescription>
              How files for this template are formatted.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <FieldGroup>
              <Controller
                name="file_format"
                control={form.control}
                render={({ field, fieldState }) => (
                  <Field data-invalid={fieldState.invalid}>
                    <FieldLabel htmlFor="file_format">File format</FieldLabel>
                    <Select
                      name={field.name}
                      value={field.value}
                      onValueChange={field.onChange}
                    >
                      <SelectTrigger id="file_format">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="csv">CSV</SelectItem>
                        <SelectItem value="xlsx">XLSX (Excel)</SelectItem>
                      </SelectContent>
                    </Select>
                    <FieldDescription>
                      The expected format of uploaded files for this template.
                    </FieldDescription>
                  </Field>
                )}
              />

              <Controller
                name="delimiter"
                control={form.control}
                render={({ field, fieldState }) => (
                  <Field data-invalid={fieldState.invalid}>
                    <FieldLabel htmlFor="delimiter">Delimiter</FieldLabel>
                    <Input
                      {...field}
                      id="delimiter"
                      placeholder=","
                      aria-invalid={fieldState.invalid}
                      maxLength={5}
                      className="max-w-[100px] font-mono"
                    />
                    <FieldDescription>
                      Field separator. Common values: <code>,</code>{' '}
                      (comma), <code>;</code> (semicolon), <code>\t</code>{' '}
                      (tab), <code>|</code> (pipe). Only applies to CSV.
                    </FieldDescription>
                    {fieldState.invalid && (
                      <FieldError errors={[fieldState.error]} />
                    )}
                  </Field>
                )}
              />

              <Controller
                name="encoding"
                control={form.control}
                render={({ field, fieldState }) => (
                  <Field data-invalid={fieldState.invalid}>
                    <FieldLabel htmlFor="encoding">Encoding</FieldLabel>
                    <Select
                      name={field.name}
                      value={field.value}
                      onValueChange={field.onChange}
                    >
                      <SelectTrigger id="encoding">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="UTF-8">UTF-8 (recommended)</SelectItem>
                        <SelectItem value="UTF-16">UTF-16</SelectItem>
                        <SelectItem value="latin-1">Latin-1</SelectItem>
                        <SelectItem value="windows-1252">windows-1252</SelectItem>
                      </SelectContent>
                    </Select>
                    <FieldDescription>
                      Text encoding of the source files. UTF-8 works for
                      almost everything; pick another if your files
                      contain non-ASCII characters that aren't displaying
                      correctly.
                    </FieldDescription>
                    {fieldState.invalid && (
                      <FieldError errors={[fieldState.error]} />
                    )}
                  </Field>
                )}
              />
            </FieldGroup>
          </CardContent>
        </Card>

        {/* Write behavior */}
        <Card>
          <CardHeader>
            <CardTitle>Write behavior</CardTitle>
            <CardDescription>
              How uploaded data is written to the target Unity
              Catalog table.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <FieldGroup>
              <Controller
                name="write_mode"
                control={form.control}
                render={({ field, fieldState }) => (
                  <Field data-invalid={fieldState.invalid}>
                    <FieldLabel htmlFor="write_mode">Write mode</FieldLabel>
                    <Select
                      name={field.name}
                      value={field.value}
                      onValueChange={field.onChange}
                    >
                      <SelectTrigger id="write_mode">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="append">Append</SelectItem>
                        <SelectItem value="overwrite">Overwrite</SelectItem>
                      </SelectContent>
                    </Select>
                    <FieldDescription>
                      <strong>Append:</strong> new rows are added to
                      the existing table. <strong>Overwrite:</strong>{' '}
                      every upload replaces all rows.
                    </FieldDescription>
                  </Field>
                )}
              />

              <Controller
                name="reader_group"
                control={form.control}
                render={({ field, fieldState }) => (
                  <Field data-invalid={fieldState.invalid}>
                    <FieldLabel htmlFor="reader_group">
                      Reader group{' '}
                      <span className="text-slate-400 font-normal">
                        (optional)
                      </span>
                    </FieldLabel>
                    <Input
                      {...field}
                      id="reader_group"
                      placeholder="e.g. finance-readers"
                      aria-invalid={fieldState.invalid}
                      maxLength={255}
                    />
                    <FieldDescription>
                      Azure AD group that gets SELECT access on the
                      target table. Leave empty if access is managed
                      separately. Configured at DDL time.
                    </FieldDescription>
                    {fieldState.invalid && (
                      <FieldError errors={[fieldState.error]} />
                    )}
                  </Field>
                )}
              />
            </FieldGroup>
          </CardContent>
        </Card>

        {/* Validation */}
        <Card>
          <CardHeader>
            <CardTitle>Validation</CardTitle>
            <CardDescription>
              What happens when uploaded files have rows that fail
              validation.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <FieldGroup>
              <Controller
                name="bad_row_threshold"
                control={form.control}
                render={({ field, fieldState }) => (
                  <Field data-invalid={fieldState.invalid}>
                    <FieldLabel htmlFor="bad_row_threshold">
                      Bad row threshold
                    </FieldLabel>
                    <div className="flex items-center gap-2">
                      <Input
                        id="bad_row_threshold"
                        type="number"
                        min={0}
                        max={100}
                        step={0.01}
                        value={field.value}
                        onChange={(e) =>
                          field.onChange(
                            e.target.value === ''
                              ? 0
                              : parseFloat(e.target.value)
                          )
                        }
                        aria-invalid={fieldState.invalid}
                        className="max-w-[120px]"
                      />
                      <span className="text-sm text-slate-600">%</span>
                    </div>
                    <FieldDescription>
                      Maximum percentage of rows that can fail
                      validation before the entire upload is treated
                      as a failure. Range 0 to 100. Default 5.
                    </FieldDescription>
                    {fieldState.invalid && (
                      <FieldError errors={[fieldState.error]} />
                    )}
                  </Field>
                )}
              />

              <Controller
                name="bad_row_action"
                control={form.control}
                render={({ field, fieldState }) => (
                  <Field data-invalid={fieldState.invalid}>
                    <FieldLabel htmlFor="bad_row_action">
                      Bad row action
                    </FieldLabel>
                    <Select
                      name={field.name}
                      value={field.value}
                      onValueChange={field.onChange}
                    >
                      <SelectTrigger id="bad_row_action">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="fail">Fail the upload</SelectItem>
                        <SelectItem value="drop">Drop bad rows and continue</SelectItem>
                      </SelectContent>
                    </Select>
                    <FieldDescription>
                      <strong>Fail:</strong> any bad row above the
                      threshold rejects the whole file.{' '}
                      <strong>Drop:</strong> bad rows are skipped;
                      valid rows still land in the table.
                    </FieldDescription>
                  </Field>
                )}
              />
            </FieldGroup>
          </CardContent>
        </Card>

        {apiError && (
          <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">
            {apiError.message}
          </div>
        )}
      </form>

      {/* Action buttons */}
      <div className="flex justify-between">
        <Button
          type="button"
          variant="outline"
          onClick={() => navigate('/templates')}
          disabled={saveMutation.isPending}
        >
          Cancel
        </Button>
        <Button
          type="submit"
          form="template-settings-form"
          disabled={saveMutation.isPending}
        >
          {saveMutation.isPending ? 'Saving...' : 'Next: Columns'}
        </Button>
      </div>
    </WizardShell>
  )
}