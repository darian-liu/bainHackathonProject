import { Database } from 'lucide-react'

export function Navbar() {
  return (
    <header className="h-14 border-b bg-white flex items-center px-4">
      <div className="flex items-center gap-2">
        <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
          <Database className="w-5 h-5 text-primary-foreground" />
        </div>
        <span className="font-semibold text-lg">Bain Productivity Tool</span>
      </div>
    </header>
  )
}
