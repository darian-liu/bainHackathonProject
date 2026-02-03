import { Outlet } from 'react-router-dom'
import { Navbar } from './Navbar'
import { ModuleSidebar } from './ModuleSidebar'
import { AgentVisualizerSidebar } from '@/components/agent-visualizer/AgentVisualizerSidebar'

export function AppShell() {
  return (
    <div className="h-screen flex flex-col">
      <Navbar />
      <div className="flex-1 flex overflow-hidden">
        <ModuleSidebar />
        <main className="flex-1 overflow-auto bg-slate-50">
          <Outlet />
        </main>
        <AgentVisualizerSidebar />
      </div>
    </div>
  )
}
