/**
 * Expert Networks Module - Entry point and module definition
 */

import { Users } from 'lucide-react'
import { Routes, Route } from 'react-router-dom'
import { ProjectListPage } from './ProjectListPage'
import { TrackerPage } from './TrackerPage'
import { IngestPage } from './IngestPage'
import type { WorkflowModule } from '../module-registry'

// Main module component with routing
function ExpertNetworksApp() {
  return (
    <Routes>
      <Route index element={<ProjectListPage />} />
      <Route path=":projectId/tracker" element={<TrackerPage />} />
      <Route path=":projectId/ingest" element={<IngestPage />} />
    </Routes>
  )
}

// Module definition for registry
export const ExpertNetworksModule: WorkflowModule = {
  id: 'expert-networks',
  name: 'Expert Networks',
  description: 'AI-powered expert screening & consolidation',
  icon: Users,
  path: '/expert-networks',
  component: ExpertNetworksApp,
}
