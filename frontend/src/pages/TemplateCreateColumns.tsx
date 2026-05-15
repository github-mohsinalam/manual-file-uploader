/**
 * Template Create Wizard - Step 2 (Columns).
 *
 * Flow:
 *   1. User uploads a sample file (or sees existing columns if revisiting)
 *   2. Backend parses with Polars, returns inferred column schema
 *   3. UI renders one editable row per column
 *   4. User edits names, types, flags, descriptions
 *   5. On Next, POST the column list to the backend
 *   6. Navigate to Step 3 (reviewers)
 *
 * State management is via react-hook-form's useFieldArray, which
 * handles dynamic array fields (add, remove, replace).
 */

import { useEffect, useRef } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Controller, useFieldArray, useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { z } from 'zod'
import { Plus, Trash2, Upload, FileText } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Field,
  FieldError
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
import { useTemplateColumns } from '@/hooks/useTemplateColumns'
import {
  parseSampleFile,
  type ParsedColumn,
} from '@/services/templates'
import { replaceTemplateColumns } from '@/services/template-columns'
import { toApiError } from '@/lib/api/client'

/**
 * Allowed Unity Catalog data types. Matches the backend
 * ColumnDataType enum in the SQL CHECK constraint.
 */
const DATA_TYPES = [
  'STRING',
  'INTEGER',
  'BIGINT',
  'LONG',
  'DOUBLE',
  'DECIMAL',
  'BOOLEAN',
  'DATE',
  'TIMESTAMP',
] as const

/**
 * Validation schema for a single column row.
 * Mirrors the backend's TemplateColumnCreate.
 */
const columnSchema = z.object({
  column_name: z
    .string()
    .min(1, 'Required')
    .regex(
      /^[a-z][a-z0-9_]*$/,
      'Lowercase letters, digits, and underscores; must start with a letter'
    ),
  display_name: z.string().optional(),
  data_type: z.enum(DATA_TYPES),
  description: z.string().optional(),
  is_included: z.boolean(),
  is_pii: z.boolean(),
  is_nullable: z.boolean(),
  is_unique: z.boolean(),
})

/**
 * Validation schema for the full columns form.
 *
 * The "name uniqueness within this form" check uses zod's
 * .refine() - lets us run cross-field validation.
 */
const columnsSchema = z.object({
  columns: z
    .array(columnSchema)
    .min(1, 'At least one column is required')
    .refine(
      (cols) => {
        const names = cols.map((c) => c.column_name.toLowerCase())
        return new Set(names).size === names.length
      },
      { message: 'Column names must be unique' }
    ),
})

type ColumnsFormValues = z.infer<typeof columnsSchema>

/**
 * Default empty column for new rows added manually.
 * Field defaults that don't need user attention to be valid.
 */
function emptyColumn() {
  return {
    column_name: '',
    display_name: '',
    data_type: 'STRING' as const,
    description: '',
    is_included: true,
    is_pii: false,
    is_nullable: true,
    is_unique: false,
  }
}

/**
 * Translate a parsed column from the backend into a form row.
 * The parser only gives us name, type, and sample values - we
 * default everything else.
 */
function parsedToRow(parsed: ParsedColumn) {
  return {
    column_name: parsed.column_name,
    display_name: '',
    data_type: parsed.data_type as (typeof DATA_TYPES)[number],
    description: '',
    is_included: true,
    is_pii: false,
    is_nullable: true,
    is_unique: false,
  }
}

export default function TemplateCreateColumns() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Fetch any columns the user has already saved (e.g. if they
  // navigated away mid-wizard and came back).
  const existingColumnsQuery = useTemplateColumns(id)

  const form = useForm<ColumnsFormValues>({
    resolver: zodResolver(columnsSchema),
    defaultValues: {
      columns: [],
    },
  })

  const { fields, append, remove, replace } = useFieldArray({
    control: form.control,
    name: 'columns',
  })

  // When the page loads, if backend returns existing columns,
  // prefill the form once.
  // useEffect with a ref-guard prevents this firing on every render.
  const hydratedRef = useRef(false)
  useEffect(() => {
    if (hydratedRef.current) return
    if (!existingColumnsQuery.data) return

    if (existingColumnsQuery.data.length > 0) {
      const rows = existingColumnsQuery.data.map((c) => ({
        column_name: c.column_name,
        display_name: c.display_name ?? '',
        data_type: c.data_type as (typeof DATA_TYPES)[number],
        description: c.description ?? '',
        is_included: c.is_included,
        is_pii: c.is_pii,
        is_nullable: c.is_nullable,
        is_unique: c.is_unique,
      }))
      replace(rows)
    }
    hydratedRef.current = true
  }, [existingColumnsQuery.data, replace])

  // Mutation 1: parse the uploaded sample file.
  const parseMutation = useMutation({
    mutationFn: (file: File) => parseSampleFile(file),
    onSuccess: (data) => {
      // Replace the entire columns list with the parsed rows.
      const rows = data.columns.map(parsedToRow)
      replace(rows)
    },
  })

  // Mutation 2: save the column list to the backend.
  const saveMutation = useMutation({
    mutationFn: (columns: ColumnsFormValues['columns']) =>
      replaceTemplateColumns(id!, columns),
    onSuccess: () => {
      // Invalidate any cached column query for this template.
      queryClient.invalidateQueries({
        queryKey: ['template-columns', id],
      })
      // Move to step 3.
      navigate(`/templates/new/${id}/reviewers`)
    },
  })

  function handleFileInputChange(
    e: React.ChangeEvent<HTMLInputElement>
  ) {
    const file = e.target.files?.[0]
    if (!file) return
    parseMutation.mutate(file)
    // Reset the input so picking the same file again re-fires onChange.
    e.target.value = ''
  }

  function onSubmit(values: ColumnsFormValues) {
    saveMutation.mutate(values.columns)
  }

  const parseError = parseMutation.error
    ? toApiError(parseMutation.error)
    : null
  const saveError = saveMutation.error
    ? toApiError(saveMutation.error)
    : null

  // The non-field-level error from the array-uniqueness refine
  // shows up at form.formState.errors.columns?.root
  const rootError = form.formState.errors.columns?.root?.message
    ?? form.formState.errors.columns?.message

  return (
    <WizardShell
      currentStep={2}
      title="Configure columns"
      description="Upload a sample file to auto-detect columns, or add them manually."
    >
      {/* Upload card */}
      <Card>
        <CardHeader>
          <CardTitle>Sample file</CardTitle>
          <CardDescription>
            Upload a CSV or XLSX file to auto-populate column names
            and inferred types. You can edit everything below before
            saving.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,.xlsx"
            onChange={handleFileInputChange}
            className="hidden"
          />
          <div className="flex items-center gap-3">
            <Button
              type="button"
              variant="outline"
              onClick={() => fileInputRef.current?.click()}
              disabled={parseMutation.isPending}
            >
              <Upload size={14} />
              {parseMutation.isPending ? 'Parsing...' : 'Upload sample file'}
            </Button>
            {parseMutation.isSuccess && (
              <span className="text-sm text-slate-600 flex items-center gap-1">
                <FileText size={14} />
                Parsed {parseMutation.data.columns.length} columns from{' '}
                {parseMutation.data.total_rows_scanned} rows
              </span>
            )}
          </div>
          {parseError && (
            <div className="mt-3 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">
              {parseError.message}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Columns form card */}
      <form
        id="columns-form"
        onSubmit={form.handleSubmit(onSubmit)}
      >
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Columns ({fields.length})</CardTitle>
                <CardDescription>
                  Configure each column's type and constraints.
                </CardDescription>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => append(emptyColumn())}
              >
                <Plus size={14} />
                Add column
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {fields.length === 0 && (
              <p className="text-sm text-slate-500 py-4">
                No columns yet. Upload a sample file or add a column
                manually.
              </p>
            )}

            {fields.length > 0 && (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-20 text-center">Include</TableHead>
                    <TableHead className="w-40">Column name</TableHead>
                    <TableHead className="w-32">Type</TableHead>
                    <TableHead className="w-20 text-center">Null</TableHead>
                    <TableHead className="w-20 text-center">Unique</TableHead>
                    <TableHead className="w-20 text-center">PII</TableHead>
                    <TableHead>Description</TableHead>
                    <TableHead className="w-12"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {fields.map((row, index) => (
                    <ColumnRow
                      key={row.id}
                      index={index}
                      control={form.control}
                      onRemove={() => remove(index)}
                    />
                  ))}
                </TableBody>
              </Table>
            )}

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
          onClick={() => navigate('/templates/new')}
          disabled={saveMutation.isPending}
        >
          Back
        </Button>
        <Button
          type="submit"
          form="columns-form"
          disabled={saveMutation.isPending || fields.length === 0}
        >
          {saveMutation.isPending ? 'Saving...' : 'Next: Reviewers'}
        </Button>
      </div>
    </WizardShell>
  )
}

/**
 * One editable row in the columns table.
 *
 * Pulled into its own component so the .map() callback stays tidy.
 * Each row owns 6 Controllers (one per editable cell + flags).
 *
 * The `control` prop is typed loosely with `any` because passing
 * the precisely-typed Control object across a component boundary
 * triggers TypeScript narrowing complexity that isn't worth fighting.
 * react-hook-form's runtime behavior is unaffected.
 */
function ColumnRow({
  index,
  control,
  onRemove,
}: {
  index: number
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  control: any
  onRemove: () => void
}) {
  return (
    <TableRow>
      {/* Include */}
      <TableCell className="text-center">
        <Controller
          name={`columns.${index}.is_included`}
          control={control}
          render={({ field }) => (
            <Checkbox
              checked={field.value}
              onCheckedChange={field.onChange}
            />
          )}
        />
      </TableCell>
      {/* Column name */}
      <TableCell>
        <Controller
          name={`columns.${index}.column_name`}
          control={control}
          render={({ field, fieldState }) => (
            <Field data-invalid={fieldState.invalid}>
              <Input
                {...field}
                aria-invalid={fieldState.invalid}
                placeholder="column_name"
                className="h-8"
              />
              {fieldState.invalid && (
                <FieldError errors={[fieldState.error]} />
              )}
            </Field>
          )}
        />
      </TableCell>

      {/* Data type */}
      <TableCell>
        <Controller
          name={`columns.${index}.data_type`}
          control={control}
          render={({ field }) => (
            <Select value={field.value} onValueChange={field.onChange}>
              <SelectTrigger className="h-8">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {DATA_TYPES.map((t) => (
                  <SelectItem key={t} value={t}>
                    {t}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        />
      </TableCell>

      {/* Nullable */}
      <TableCell className="text-center">
        <Controller
          name={`columns.${index}.is_nullable`}
          control={control}
          render={({ field }) => (
            <Checkbox
              checked={field.value}
              onCheckedChange={field.onChange}
            />
          )}
        />
      </TableCell>

      {/* Unique */}
      <TableCell className="text-center">
        <Controller
          name={`columns.${index}.is_unique`}
          control={control}
          render={({ field }) => (
            <Checkbox
              checked={field.value}
              onCheckedChange={field.onChange}
            />
          )}
        />
      </TableCell>

      {/* PII */}
      <TableCell className="text-center">
        <Controller
          name={`columns.${index}.is_pii`}
          control={control}
          render={({ field }) => (
            <Checkbox
              checked={field.value}
              onCheckedChange={field.onChange}
            />
          )}
        />
      </TableCell>

      {/* Description */}
      <TableCell>
        <Controller
          name={`columns.${index}.description`}
          control={control}
          render={({ field }) => (
            <Textarea
              {...field}
              placeholder="Optional"
              rows={1}
              className="min-h-8 text-sm"
            />
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
          className="h-8 w-8 p-0"
        >
          <Trash2 size={14} />
        </Button>
      </TableCell>
    </TableRow>
  )
}