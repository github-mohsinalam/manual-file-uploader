/**
 * Application route definitions.
 *
 * BrowserRouter activates client-side routing — listening to
 * URL changes and rendering the matching route.
 *
 * The Routes block declares the URL-to-component mapping.
 * Nested Routes share a common Layout — only the inner content
 * (rendered via the Layout's Outlet) changes between them.
 *
 * Catch-all "*" matches any path not covered by other routes
 * and renders NotFound.
 */

import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
} from 'react-router-dom'

import { Layout } from '@/components/layout/Layout'
import TemplatesList from '@/pages/TemplatesList'
import TemplateDetail from '@/pages/TemplateDetail'
import UploadsList from '@/pages/UploadsList'
import Domains from '@/pages/Domains'
import About from '@/pages/About'
import NotFound from '@/pages/NotFound'
import TemplateCreateBasics from '@/pages/TemplateCreateBasics'
import TemplateCreateColumns from '@/pages/TemplateCreateColumns'
import TemplateCreateReviewers from '@/pages/TemplateCreateReviewers'
import TemplateCreateReview from '@/pages/TemplateCreateReview'
import TemplateWizardEntry from '@/pages/TemplateWizardEntry'
import ApprovalPage from '@/pages/ApprovalPage'
import TemplateUpload from '@/pages/TemplateUpload'
import UploadProgress from '@/pages/UploadProgress'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public route - no Layout (no sidebar, no nav).
          Used by reviewers landing from email links. */}
        <Route path="/approve" element={<ApprovalPage />} />
        {/* Layout wraps every page below it */}
        <Route element={<Layout />}>
          {/* Root URL redirects to /templates */}
          <Route path="/" element={<Navigate to="/templates" replace />} />

          <Route path="/templates" element={<TemplatesList />} />
          <Route path="/templates/new" element={<TemplateCreateBasics />} />
          <Route path="/templates/new/:id" element={<TemplateWizardEntry />} />
          <Route path="/templates/:id/upload" element={<TemplateUpload />} />
          <Route path="/templates/new/:id/columns" element={<TemplateCreateColumns />} />
          <Route path="/templates/new/:id/reviewers" element={<TemplateCreateReviewers />} />
          <Route path="/templates/new/:id/review" element={<TemplateCreateReview />} />
          <Route path="/templates/:id" element={<TemplateDetail />} />
          <Route path="/uploads" element={<UploadsList />} />
          <Route path="/uploads/:id" element={<UploadProgress />} />
          <Route path="/domains" element={<Domains />} />
          <Route path="/about" element={<About />} />

          {/* Catch-all 404 */}
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App