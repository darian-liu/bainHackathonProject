import { Outlet } from 'react-router-dom'
import { AppSidebar } from './AppSidebar'
import { AgentVisualizerSidebar } from '@/components/agent-visualizer/AgentVisualizerSidebar'

export function AppShell() {
  return (
    <div className="h-screen flex overflow-hidden">
      <AppSidebar />
      <main className="flex-1 overflow-auto bg-slate-50">
        <Outlet />
      </main>
      <AgentVisualizerSidebar />
    </div>
  )
}
