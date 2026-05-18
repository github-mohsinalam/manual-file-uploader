/**
 * Template Upload Page.
 *
 * Lets the user upload a CSV or XLSX file for an Approved
 * template. Shows the expected schema as reference, accepts
 * the file via click or drag-and-drop, validates client-side
 * (extension + size), then POSTs as multipart form data.
 *
 * On success, navigates to the progress page (Task 9.16) which
 * polls the upload status until terminal.
 *
 * Only Approved templates accept uploads. The backend enforces
 * this; we also surface a friendly message if a user lands
 * here with a non-Approved template.
 */

import { useRef, useState } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import {
  ArrowLeft,
  FileText,
  Upload,
  X,
  AlertTriangle,
} from 'lucide-react'

import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

import { useTemplate } from '@/hooks/useTemplate'
import { submitUpload } from '@/services/uploads'
import { toApiError } from '@/lib/api/client'
import { cn } from '@/lib/utils'

/** Max file size in MB - matches the backend setting. */
const MAX_FILE_SIZE_MB = 100

/** Allowed file extensions. */
const ALLOWED_EXTENSIONS = ['csv', 'xlsx'] as const

export default function TemplateUpload() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const templateQuery = useTemplate(id)

  const fileInputRef = useRef<HTMLInputElement>(null)

  // The selected file (from picker or drop). Single file only.
  const [file, setFile] = useState<File | null>(null)
  // Visual flag for drag-over state.
  const [isDragOver, setIsDragOver] = useState(false)
  // Client-side validation error message (no file != error).
  const [validationError, setValidationError] = useState<string | null>(null)
  // Upload progress percent (0-100).
  const [uploadProgress, setUploadProgress] = useState(0)

  const uploadMutation = useMutation({
    mutationFn: (selected: File) =>
      submitUpload(id!, selected, setUploadProgress),
    onSuccess: (result) => {
      // Reset local progress
      setUploadProgress(0)
      // Navigate to the progress page (built in Task 9.16).
      navigate(`/uploads/${result.id}`)
    },
  })

  function validateFile(candidate: File): string | null {
    const extension = candidate.name
      .split('.')
      .pop()
      ?.toLowerCase()

    if (!extension || !ALLOWED_EXTENSIONS.includes(extension as never)) {
      return `Unsupported file format. Use ${ALLOWED_EXTENSIONS
        .map((e) => `.${e}`)
        .join(' or ')}.`
    }

    const sizeMb = candidate.size / (1024 * 1024)
    if (sizeMb > MAX_FILE_SIZE_MB) {
      return `File is ${sizeMb.toFixed(1)} MB - exceeds the ${MAX_FILE_SIZE_MB} MB limit.`
    }

    return null
  }

  function handleFileSelected(candidate: File) {
    const err = validateFile(candidate)
    if (err) {
      setValidationError(err)
      setFile(null)
      return
    }
    setValidationError(null)
    setFile(candidate)
  }

  function handleFileInputChange(
    e: React.ChangeEvent<HTMLInputElement>
  ) {
    const candidate = e.target.files?.[0]
    if (candidate) {
      handleFileSelected(candidate)
    }
    // Reset the input so re-picking the same file fires onChange.
    e.target.value = ''
  }

  function handleDrop(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault()
    setIsDragOver(false)
    const candidate = e.dataTransfer.files?.[0]
    if (candidate) {
      handleFileSelected(candidate)
    }
  }

  function handleUploadClick() {
    if (file) {
      uploadMutation.mutate(file)
    }
  }

  // ---- Render states ----

  if (templateQuery.isLoading || !templateQuery.data) {
    return <PageSkeleton />
  }

  if (templateQuery.error) {
    return (
      <div className="space-y-4">
        <Back />
        <Card>
          <CardContent className="pt-6">
            <p className="text-red-600">
              Failed to load template:{' '}
              {(templateQuery.error as Error).message}
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }

  const template = templateQuery.data

  // Guardrail - only Approved templates accept uploads. The
  // backend rejects with 400 anyway, but we give a friendlier
  // message here so the user doesn't even start the flow.
  if (template.status !== 'Approved') {
    return (
      <div className="space-y-6">
        <Back />
        <div>
          <h1 className="text-3xl font-bold text-slate-900">
            Upload data file
          </h1>
          <p className="text-slate-600 mt-1">{template.display_name}</p>
        </div>
        <Card className="bg-amber-50 border-amber-200">
          <CardContent className="pt-6">
            <div className="flex gap-3">
              <AlertTriangle
                className="text-amber-600 shrink-0 mt-0.5"
                size={20}
              />
              <div className="text-sm text-amber-900 space-y-1">
                <p className="font-medium">Template not ready for uploads</p>
                <p>
                  This template is in status{' '}
                  <strong>{template.status}</strong>. Uploads are only
                  accepted for Approved templates. The Unity Catalog
                  table must exist before data can be ingested.
                </p>
                <Link
                  to={`/templates/${template.id}`}
                  className="inline-block mt-2 text-amber-900 underline"
                >
                  Back to template
                </Link>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  const submitError = uploadMutation.error
    ? toApiError(uploadMutation.error)
    : null

  return (
    <div className="space-y-6">
      <Back />

      <div>
        <h1 className="text-3xl font-bold text-slate-900">
          Upload data file
        </h1>
        <p className="text-slate-600 mt-1">
          {template.display_name}{' '}
          <span className="text-slate-400">
            (<code className="text-sm">{template.fully_qualified_name}</code>)
          </span>
        </p>
      </div>
      {/* File picker / drop zone */}
      <Card>
        <CardHeader>
          <CardTitle>Choose file</CardTitle>
          <CardDescription>
            CSV or XLSX, up to {MAX_FILE_SIZE_MB} MB.
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

          {!file && (
            <div
              onClick={() => fileInputRef.current?.click()}
              onDragOver={(e) => {
                e.preventDefault()
                setIsDragOver(true)
              }}
              onDragLeave={() => setIsDragOver(false)}
              onDrop={handleDrop}
              className={cn(
                'cursor-pointer rounded-lg border-2 border-dashed p-12 text-center transition-colors',
                isDragOver
                  ? 'border-indigo-500 bg-indigo-50'
                  : 'border-slate-300 hover:border-slate-400'
              )}
            >
              <FileText
                className="mx-auto text-slate-400 mb-2"
                size={32}
              />
              <p className="text-sm text-slate-700 font-medium">
                Click to choose file
              </p>
              <p className="text-xs text-slate-500 mt-1">
                or drag and drop here
              </p>
            </div>
          )}

          {file && (
            <div className="flex items-center gap-3 rounded-md border border-slate-200 bg-slate-50 p-3">
              <FileText
                className="text-slate-500 shrink-0"
                size={20}
              />
              <div className="flex-1 min-w-0">
                <div className="font-medium text-slate-900 truncate">
                  {file.name}
                </div>
                <div className="text-xs text-slate-500">
                  {formatBytes(file.size)}
                </div>
              </div>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setFile(null)}
                disabled={uploadMutation.isPending}
                className="h-8 w-8 p-0 shrink-0"
              >
                <X size={14} />
              </Button>
            </div>
          )}

          {validationError && (
            <div className="mt-3 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">
              {validationError}
            </div>
          )}

          {uploadMutation.isPending && uploadProgress > 0 && (
            <div className="mt-3 space-y-1">
              <div className="text-xs text-slate-600">
                Uploading... {uploadProgress}%
              </div>
              <div className="w-full bg-slate-200 rounded-full h-2 overflow-hidden">
                <div
                  className="bg-indigo-600 h-full transition-all duration-150"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          )}

          {submitError && (
            <div className="mt-3 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">
              {submitError.message}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Action buttons */}
      <div className="flex justify-between">
        <Button
          type="button"
          variant="outline"
          onClick={() => navigate(`/templates/${template.id}`)}
          disabled={uploadMutation.isPending}
        >
          Cancel
        </Button>
        <Button
          onClick={handleUploadClick}
          disabled={!file || uploadMutation.isPending}
        >
          <Upload size={14} />
          {uploadMutation.isPending ? 'Uploading...' : 'Upload'}
        </Button>
      </div>
    </div>
  )
}

/** Back link to the template detail page. */
function Back() {
  const { id } = useParams<{ id: string }>()
  return (
    <Link
      to={`/templates/${id}`}
      className="inline-flex items-center gap-1 text-sm text-slate-600 hover:text-slate-900"
    >
      <ArrowLeft size={14} />
      Back to template
    </Link>
  )
}

/** Skeleton while the template fetch is in flight. */
function PageSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-4 w-32" />
      <div className="space-y-2">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-4 w-96" />
      </div>
      <Skeleton className="h-48 w-full" />
      <Skeleton className="h-48 w-full" />
    </div>
  )
}

/** Human-readable byte size. */
function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}