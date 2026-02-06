import { NavLink, useNavigate, useLocation } from 'react-router-dom'
import { Sparkles, Plus, Bot, Settings, FolderOpen } from 'lucide-react'
import { useProjects } from '@/modules/expert-networks/api'
import { cn } from '@/lib/utils'

export function AppSidebar() {
  const navigate = useNavigate()
  const location = useLocation()
  const { data } = useProjects()
  const projects = data?.projects || []

  const isHome = location.pathname === '/'

  return (
    <aside className="w-64 border-r bg-gray-950 text-white flex flex-col h-full">
      {/* Logo / Home link */}
      <div className="p-4 border-b border-gray-800">
        <button
          onClick={() => navigate('/')}
          className="flex items-center gap-3 w-full hover:opacity-80 transition-opacity"
        >
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-indigo-500 flex items-center justify-center shrink-0">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <span className="font-semibold text-lg">Expert AI</span>
        </button>
      </div>

      {/* New Project button */}
      <div className="p-3">
        <button
          onClick={() => navigate('/')}
          className={cn(
            'flex items-center gap-2 w-full px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
            isHome
              ? 'bg-gray-800 text-white'
              : 'text-gray-400 hover:bg-gray-800/50 hover:text-white'
          )}
        >
          <Plus className="w-4 h-4" />
          New Project
        </button>
      </div>

      {/* Projects list */}
      <div className="flex-1 overflow-auto px-3 pb-3">
        {projects.length > 0 && (
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wider px-3 mb-2">
              Projects
            </p>
            <div className="space-y-0.5">
              {projects.map((project) => {
                const projectPath = `/expert-networks/${project.id}/tracker`
                const isActive = location.pathname.includes(project.id)
                return (
                  <button
                    key={project.id}
                    onClick={() => navigate(projectPath)}
                    className={cn(
                      'flex items-center gap-2 w-full px-3 py-2 rounded-lg text-sm transition-colors text-left',
                      isActive
                        ? 'bg-gray-800 text-white'
                        : 'text-gray-400 hover:bg-gray-800/50 hover:text-gray-200'
                    )}
                  >
                    <FolderOpen className="w-4 h-4 shrink-0" />
                    <span className="truncate">{project.name}</span>
                  </button>
                )
              })}
            </div>
          </div>
        )}
      </div>

      {/* Bottom utility links */}
      <div className="border-t border-gray-800 p-3 space-y-0.5">
        <NavLink
          to="/agent"
          className={({ isActive }) =>
            cn(
              'flex items-center gap-2 w-full px-3 py-2 rounded-lg text-sm transition-colors',
              isActive
                ? 'bg-gray-800 text-white'
                : 'text-gray-400 hover:bg-gray-800/50 hover:text-gray-200'
            )
          }
        >
          <Bot className="w-4 h-4" />
          AI Agent
        </NavLink>
        <NavLink
          to="/settings"
          className={({ isActive }) =>
            cn(
              'flex items-center gap-2 w-full px-3 py-2 rounded-lg text-sm transition-colors',
              isActive
                ? 'bg-gray-800 text-white'
                : 'text-gray-400 hover:bg-gray-800/50 hover:text-gray-200'
            )
          }
        >
          <Settings className="w-4 h-4" />
          Settings
        </NavLink>
      </div>
    </aside>
  )
}
