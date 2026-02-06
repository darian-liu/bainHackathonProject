import { useState, useEffect } from 'react'
import { AgentChat } from './AgentChat'
import { ContextPanel } from './ContextPanel'
import { useAgentStore } from '@/stores/agentStore'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

interface ProjectOption {
  id: string
  name: string
}

export function AgentPage() {
  const [showContext, setShowContext] = useState(false)
  const [projects, setProjects] = useState<ProjectOption[]>([])
  const { loadTools, projectId, setProjectId } = useAgentStore()

  // Fetch projects for the selector
  useEffect(() => {
    loadTools()
    fetch(`${API_BASE}/api/expert-networks/projects`)
      .then(res => res.ok ? res.json() : { projects: [] })
      .then(data => setProjects(data.projects || []))
      .catch(() => setProjects([]))
  }, [loadTools])

  return (
    <div className="h-full flex">
      {/* Main chat area */}
      <div className="flex-1 flex flex-col">
        {/* Project selector header */}
        <div className="px-6 py-3 border-b bg-gray-50 flex items-center gap-4">
          <label className="text-sm font-medium whitespace-nowrap">Expert Project:</label>
          <select
            className="border rounded px-3 py-1.5 text-sm w-64 bg-white"
            value={projectId || ''}
            onChange={(e) => setProjectId(e.target.value || null)}
          >
            <option value="">Select project for expert queries</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </div>

        <AgentChat onToggleTools={() => setShowContext(!showContext)} />
      </div>

      {/* Right panel: Context files */}
      {showContext && (
        <div className="w-80 border-l bg-white flex flex-col">
          <ContextPanel />
        </div>
      )}
    </div>
  )
}
