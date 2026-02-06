import { NavLink, useNavigate, useLocation } from 'react-router-dom'
import { Sparkles, Plus, Bot, Settings, FolderOpen, Users, FileText, BarChart3, Lock } from 'lucide-react'
import { useProjects } from '@/modules/expert-networks/api'
import { cn } from '@/lib/utils'

export function AppSidebar() {
  const navigate = useNavigate()
  const location = useLocation()
  const { data } = useProjects()
  const projects = data?.projects || []

  const isHome = location.pathname === '/'
  const isExpertModule = location.pathname.startsWith('/expert-networks')
  const isAgent = location.pathname.startsWith('/agent')

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
          <div className="flex flex-col items-start">
            <span className="font-semibold text-lg leading-tight">Bain AI</span>
            <span className="text-[10px] text-gray-500 leading-tight">Diligence Platform</span>
          </div>
        </button>
      </div>

      {/* Modules section */}
      <div className="px-3 pt-3 pb-1">
        <p className="text-[10px] font-semibold text-gray-600 uppercase tracking-widest px-3 mb-2">
          Modules
        </p>

        {/* Expert Networks — active module */}
        <button
          onClick={() => navigate('/')}
          className={cn(
            'flex items-center gap-2.5 w-full px-3 py-2 rounded-lg text-sm font-medium transition-colors',
            (isHome || isExpertModule)
              ? 'bg-purple-600/20 text-purple-300 border border-purple-500/30'
              : 'text-gray-400 hover:bg-gray-800/50 hover:text-white'
          )}
        >
          <Users className="w-4 h-4 shrink-0" />
          Expert Networks
        </button>

        {/* AI Agent — active module */}
        <div className="mt-0.5">
          <button
            onClick={() => navigate('/agent')}
            className={cn(
              'flex items-center gap-2.5 w-full px-3 py-2 rounded-lg text-sm font-medium transition-colors',
              isAgent
                ? 'bg-purple-600/20 text-purple-300 border border-purple-500/30'
                : 'text-gray-400 hover:bg-gray-800/50 hover:text-white'
            )}
          >
            <Bot className="w-4 h-4 shrink-0" />
            AI Agent
          </button>
        </div>

        {/* Coming soon modules */}
        <div className="mt-0.5 space-y-0.5">
          {[
            { icon: FileText, label: 'Data Room' },
            { icon: BarChart3, label: 'Market Sizing' },
          ].map(({ icon: Icon, label }) => (
            <div
              key={label}
              className="flex items-center gap-2.5 w-full px-3 py-2 rounded-lg text-sm text-gray-600 cursor-default"
            >
              <Icon className="w-4 h-4 shrink-0" />
              <span className="flex-1">{label}</span>
              <Lock className="w-3 h-3 text-gray-700" />
            </div>
          ))}
        </div>
      </div>

      {/* Divider */}
      <div className="px-6 py-1">
        <div className="border-t border-gray-800" />
      </div>

      {/* New Project + Projects list */}
      <div className="px-3 pb-1">
        <button
          onClick={() => navigate('/')}
          className={cn(
            'flex items-center gap-2 w-full px-3 py-2 rounded-lg text-sm font-medium transition-colors',
            isHome && !isExpertModule
              ? 'bg-gray-800 text-white'
              : 'text-gray-400 hover:bg-gray-800/50 hover:text-white'
          )}
        >
          <Plus className="w-4 h-4" />
          New Project
        </button>
      </div>

      <div className="flex-1 overflow-auto px-3 pb-3">
        {projects.length > 0 && (
          <div>
            <p className="text-[10px] font-semibold text-gray-600 uppercase tracking-widest px-3 mb-2">
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
