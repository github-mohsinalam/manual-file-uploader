/**
 * Template Create Wizard - Step 1 (Basics).
 *
 * Collects:
 *   - name (technical identifier, lowercase + underscore)
 *   - display_name (human-readable)
 *   - description (optional, short)
 *   - domain_id (dropdown of seeded domains)
 *
 * Submit creates a Draft template row in the backend and
 * navigates to step 2 (columns). The new template's ID is
 * carried into the URL for subsequent steps.
 *
 * Uses the shadcn v4 Field + Controller pattern.
 */

import { useNavigate } from 'react-router-dom'
import { Controller, useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { z } from 'zod'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import {
  Field,
  FieldContent,
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
import { Card, CardContent } from '@/components/ui/card'

import { WizardShell } from '@/components/wizard/WizardShell'
import { useDomains } from '@/hooks/useDomains'
import { createTemplate } from '@/services/templates'
import { toApiError } from '@/lib/api/client'

/**
 * Validation schema for the basics form.
 * Mirrors the backend's TemplateCreate Pydantic schema.
 */
const basicsSchema = z.object({
  name: z
    .string()
    .min(3, 'At least 3 characters')
    .max(64, 'At most 64 characters')
    .regex(
      /^[a-z][a-z0-9_]*$/,
      'Lowercase letters, digits, and underscores; must start with a letter'
    ),
  display_name: z
    .string()
    .min(3, 'At least 3 characters')
    .max(100, 'At most 100 characters'),
  description: z
    .string()
    .max(500, 'At most 500 characters')
    .optional(),
  domain_id: z
    .string()
    .uuid('Please select a domain'),
})

/** Form values type, inferred from the zod schema. */
type BasicsFormValues = z.infer<typeof basicsSchema>

export default function TemplateCreateBasics() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  // Domains populate the dropdown.
  const domainsQuery = useDomains()

  // Set up the form with zod validation.
  const form = useForm<BasicsFormValues>({
    resolver: zodResolver(basicsSchema),
    defaultValues: {
      name: '',
      display_name: '',
      description: '',
      domain_id: '',
    },
  })

  // Mutation for POST /templates.
  const createMutation = useMutation({
    mutationFn: (payload: BasicsFormValues) => createTemplate(payload),
    onSuccess: (newTemplate) => {
      // Bust the cache so the list page refreshes.
      queryClient.invalidateQueries({ queryKey: ['templates'] })
      // Move to step 2.
      navigate(`/templates/new/${newTemplate.id}/settings`)
    },
  })

  /**
   * Form submit handler. Receives values that have already passed
   * zod validation - rhf doesn't call this unless validation passes.
   */
  function onSubmit(values: BasicsFormValues) {
    createMutation.mutate(values)
  }

  // Normalize the mutation error into our standard ApiError shape.
  const apiError = createMutation.error
    ? toApiError(createMutation.error)
    : null

  return (
    <WizardShell
      currentStep={1}
      title="Create a new template"
      description="Start by giving the template a name and choosing the domain it belongs to."
    >
      <Card>
        <CardContent className="pt-6">
          <form
            id="template-basics-form"
            onSubmit={form.handleSubmit(onSubmit)}
          >
            <FieldGroup>
              {/* Name */}
              <Controller
                name="name"
                control={form.control}
                render={({ field, fieldState }) => (
                  <Field data-invalid={fieldState.invalid}>
                    <FieldLabel htmlFor="template-name">
                      Technical name
                    </FieldLabel>
                    <Input
                      {...field}
                      id="template-name"
                      placeholder="region_mapping"
                      aria-invalid={fieldState.invalid}
                      autoComplete="off"
                    />
                    <FieldDescription>
                      Used as the Unity Catalog table name. Lowercase
                      letters, digits, and underscores only. Must start
                      with a letter.
                    </FieldDescription>
                    {fieldState.invalid && (
                      <FieldError errors={[fieldState.error]} />
                    )}
                  </Field>
                )}
              />

              {/* Display name */}
              <Controller
                name="display_name"
                control={form.control}
                render={({ field, fieldState }) => (
                  <Field data-invalid={fieldState.invalid}>
                    <FieldLabel htmlFor="template-display-name">
                      Display name
                    </FieldLabel>
                    <Input
                      {...field}
                      id="template-display-name"
                      placeholder="Region Mapping"
                      aria-invalid={fieldState.invalid}
                    />
                    <FieldDescription>
                      Human-readable name shown across the UI.
                    </FieldDescription>
                    {fieldState.invalid && (
                      <FieldError errors={[fieldState.error]} />
                    )}
                  </Field>
                )}
              />

              {/* Description */}
              <Controller
                name="description"
                control={form.control}
                render={({ field, fieldState }) => (
                  <Field data-invalid={fieldState.invalid}>
                    <FieldLabel htmlFor="template-description">
                      Description{' '}
                      <span className="text-slate-400 font-normal">
                        (optional)
                      </span>
                    </FieldLabel>
                    <Textarea
                      {...field}
                      id="template-description"
                      placeholder="Maps regions to cost centers..."
                      rows={3}
                      aria-invalid={fieldState.invalid}
                    />
                    <FieldDescription>
                      Optional short description shown on the detail page.
                    </FieldDescription>
                    {fieldState.invalid && (
                      <FieldError errors={[fieldState.error]} />
                    )}
                  </Field>
                )}
              />

              {/* Domain */}
              <Controller
                name="domain_id"
                control={form.control}
                render={({ field, fieldState }) => (
                  <Field
                    orientation="responsive"
                    data-invalid={fieldState.invalid}
                  >
                    <FieldContent>
                      <FieldLabel htmlFor="template-domain">
                        Domain
                      </FieldLabel>
                      <FieldDescription>
                        Maps to a Unity Catalog schema. Domains are
                        seeded and not user-creatable.
                      </FieldDescription>
                      {fieldState.invalid && (
                        <FieldError errors={[fieldState.error]} />
                      )}
                    </FieldContent>
                    <Select
                      name={field.name}
                      value={field.value}
                      onValueChange={field.onChange}
                    >
                      <SelectTrigger
                        id="template-domain"
                        aria-invalid={fieldState.invalid}
                        className="min-w-[200px]"
                      >
                        <SelectValue placeholder="Select a domain" />
                      </SelectTrigger>
                      <SelectContent>
                        {domainsQuery.data?.map((d) => (
                          <SelectItem key={d.id} value={d.id}>
                            {d.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </Field>
                )}
              />

              {/* API error (e.g. duplicate name 400 from backend) */}
              {apiError && (
                <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">
                  {apiError.message}
                </div>
              )}
            </FieldGroup>
          </form>
        </CardContent>
      </Card>

      {/* Action buttons live OUTSIDE the <form> but use the form="..."
          attribute to bind to it - lets us place the buttons in a
          separate visual zone while still triggering form submit. */}
      <div className="flex justify-between">
        <Button
          type="button"
          variant="outline"
          onClick={() => navigate('/templates')}
          disabled={createMutation.isPending}
        >
          Cancel
        </Button>
        <Button
          type="submit"
          form="template-basics-form"
          disabled={createMutation.isPending}
        >
          {createMutation.isPending ? 'Creating...' : 'Next: Settings'}
        </Button>
      </div>
    </WizardShell>
  )
}