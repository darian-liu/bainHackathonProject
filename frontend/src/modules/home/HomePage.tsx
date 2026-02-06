import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Sparkles, ArrowRight, Loader2 } from 'lucide-react'
import { useProjects, useCreateProject } from '@/modules/expert-networks/api'

export function HomePage() {
  const navigate = useNavigate()
  const { data, isLoading: projectsLoading } = useProjects()
  const createProject = useCreateProject()
  const [input, setInput] = useState('')

  const projects = data?.projects || []

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || createProject.isPending) return

    try {
      const project = await createProject.mutateAsync({
        name: input.trim(),
        hypothesisText: input.trim(),
      })
      navigate(`/expert-networks/${project.id}/tracker`)
    } catch (error) {
      console.error('Failed to create project:', error)
    }
  }

  return (
    <div className="h-full flex flex-col items-center justify-center px-6 bg-white">
      {/* Hero section */}
      <div className="w-full max-w-2xl text-center mb-8">
        <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-purple-600 to-indigo-600 flex items-center justify-center mx-auto mb-6">
          <Sparkles className="w-8 h-8 text-white" />
        </div>
        <h1 className="text-4xl font-semibold text-gray-900 mb-3 tracking-tight">
          What do you want to become an expert in?
        </h1>
        <p className="text-lg text-gray-500">
          Start with a question. We'll help you screen experts, analyze documents, and build understanding.
        </p>
      </div>

      {/* Input box */}
      <form onSubmit={handleSubmit} className="w-full max-w-2xl mb-12">
        <div className="relative">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="e.g., Pharma supply chain due diligence..."
            className="w-full px-5 py-4 pr-14 text-base border border-gray-200 rounded-2xl shadow-sm focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent placeholder:text-gray-400 bg-gray-50"
            disabled={createProject.isPending}
          />
          <button
            type="submit"
            disabled={!input.trim() || createProject.isPending}
            className="absolute right-2 top-1/2 -translate-y-1/2 w-10 h-10 flex items-center justify-center rounded-xl bg-purple-600 text-white hover:bg-purple-700 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            {createProject.isPending ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <ArrowRight className="w-5 h-5" />
            )}
          </button>
        </div>
      </form>

      {/* Existing projects */}
      {projects.length > 0 && (
        <div className="w-full max-w-2xl">
          <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">
            Recent Projects
          </h2>
          <div className="grid gap-3 sm:grid-cols-2">
            {projects.map((project) => (
              <button
                key={project.id}
                onClick={() => navigate(`/expert-networks/${project.id}/tracker`)}
                className="text-left p-4 rounded-xl border border-gray-100 hover:border-purple-200 hover:bg-purple-50/50 transition-all group"
              >
                <p className="font-medium text-gray-900 group-hover:text-purple-700 transition-colors">
                  {project.name}
                </p>
                {project.hypothesisText && (
                  <p className="text-sm text-gray-500 mt-1 line-clamp-2">
                    {project.hypothesisText}
                  </p>
                )}
                <p className="text-xs text-gray-400 mt-2">
                  {new Date(project.createdAt).toLocaleDateString()}
                </p>
              </button>
            ))}
          </div>
        </div>
      )}

      {projectsLoading && (
        <div className="text-gray-400 text-sm">
          <Loader2 className="w-4 h-4 animate-spin inline mr-2" />
          Loading projects...
        </div>
      )}
    </div>
  )
}
