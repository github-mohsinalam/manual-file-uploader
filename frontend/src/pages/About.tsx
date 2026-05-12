/**
 * About page.
 *
 * Brief description of the application. Useful as the very
 * first page to land users on if they have no other context.
 */

export default function About() {
  return (
    <div className="space-y-4">
      <h1 className="text-3xl font-bold text-slate-900">
        About Manual File Uploader
      </h1>
      <p className="text-slate-600">
        A governance-first platform for managing manual mapping
        files and syncing them to Unity Catalog tables in Azure
        Databricks.
      </p>
      <ul className="list-disc list-inside text-slate-700 space-y-1">
        <li>Template creation with column-level configuration</li>
        <li>Multi-reviewer approval workflow</li>
        <li>File upload with row-level validation</li>
        <li>Automatic Delta table provisioning</li>
      </ul>
    </div>
  )
}