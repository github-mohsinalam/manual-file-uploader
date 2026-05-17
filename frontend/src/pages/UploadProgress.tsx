/**
 * Upload Progress Page.
 *
 * Placeholder for Task 9.16. Will poll GET /uploads/{id} until
 * status reaches a terminal state (completed, failed, partial).
 * Shows a step indicator for the 7 upload lifecycle stages.
 */

import { useParams, Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'

import { Card, CardContent } from '@/components/ui/card'

export default function UploadProgress() {
  const { id } = useParams<{ id: string }>()

  return (
    <div className="space-y-6">
      <Link
        to="/uploads"
        className="inline-flex items-center gap-1 text-sm text-slate-600 hover:text-slate-900"
      >
        <ArrowLeft size={14} />
        Back to uploads
      </Link>

      <div>
        <h1 className="text-3xl font-bold text-slate-900">
          Upload progress
        </h1>
        <p className="text-slate-600 mt-1">
          Upload ID:{' '}
          <code className="bg-slate-100 px-1 py-0.5 rounded">{id}</code>
        </p>
      </div>

      <Card>
        <CardContent className="pt-6">
          <p className="text-slate-600">
            Upload progress polling lands in Task 9.16.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}