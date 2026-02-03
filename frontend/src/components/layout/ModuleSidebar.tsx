import { NavLink } from 'react-router-dom'
import { modules } from '@/modules/module-registry'
import { cn } from '@/lib/utils'

export function ModuleSidebar() {
  return (
    <aside className="w-64 border-r bg-white p-4">
      <nav className="space-y-1">
        {modules.map((module) => {
          const Icon = module.icon
          return (
            <NavLink
              key={module.id}
              to={module.path}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-primary text-primary-foreground'
                    : 'text-slate-600 hover:bg-slate-100'
                )
              }
            >
              <Icon className="w-5 h-5" />
              <div>
                <div>{module.name}</div>
                <div className={cn(
                  'text-xs',
                  'opacity-70'
                )}>
                  {module.description}
                </div>
              </div>
            </NavLink>
          )
        })}
      </nav>
    </aside>
  )
}
