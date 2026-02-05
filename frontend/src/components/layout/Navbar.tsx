import { Sparkles } from 'lucide-react'

export function Navbar() {
  return (
    <header className="h-14 border-b bg-white flex items-center px-4">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-600 to-indigo-600 flex items-center justify-center">
          <Sparkles className="w-5 h-5 text-white" />
        </div>
        <div>
          <span className="font-semibold text-lg">Expert AI</span>
          <span className="hidden sm:inline text-sm text-gray-500 ml-2">AI-powered screening for diligence teams</span>
        </div>
      </div>
    </header>
  )
}
