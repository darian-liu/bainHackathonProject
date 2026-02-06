import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Sparkles, ArrowRight, Loader2, X, Users, FileText, BarChart3, Bot, Lock } from 'lucide-react'
import { useProjects, useCreateProject } from '@/modules/expert-networks/api'
import type { ScreenerQuestion } from '@/modules/expert-networks/types'

/**
 * Best-effort parse of bulk screener text into ScreenerQuestion[].
 * Handles patterns like:
 *   Question 1: ...
 *   Ideal answer: ...
 * Falls back to a single question with the full text if no pattern found.
 */
function parseBulkScreenerText(text: string): ScreenerQuestion[] {
  const trimmed = text.trim()
  if (!trimmed) return []

  // Try splitting on "Question N:" pattern
  const blocks = trimmed.split(/(?=question\s*\d+\s*:)/i).filter(Boolean)

  if (blocks.length <= 1 && !/^question\s*\d+\s*:/i.test(trimmed)) {
    // No structured pattern found — store as single question
    return [{
      id: 'q1',
      order: 1,
      text: trimmed,
      idealAnswer: '',
    }]
  }

  return blocks.map((block, i) => {
    // Remove the "Question N:" prefix
    const withoutPrefix = block.replace(/^question\s*\d+\s*:\s*/i, '').trim()

    // Split on "Ideal answer:" if present
    const idealMatch = withoutPrefix.split(/ideal\s*answer\s*:\s*/i)
    const questionText = (idealMatch[0] || '').trim()
    const idealAnswer = (idealMatch[1] || '').trim()

    return {
      id: `q${i + 1}`,
      order: i + 1,
      text: questionText,
      idealAnswer,
    }
  })
}

export function HomePage() {
  const navigate = useNavigate()
  const { data, isLoading: projectsLoading } = useProjects()
  const createProject = useCreateProject()
  const [input, setInput] = useState('')
  const [step, setStep] = useState<'name' | 'screener'>('name')
  const [screenerText, setScreenerText] = useState('')

  const projects = data?.projects || []

  const handleNameSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim()) return
    setStep('screener')
  }

  const handleCreateProject = async (includeScreener: boolean) => {
    if (createProject.isPending) return

    const screenerConfig = includeScreener && screenerText.trim()
      ? { questions: parseBulkScreenerText(screenerText), autoScreen: true }
      : undefined

    try {
      const project = await createProject.mutateAsync({
        name: input.trim(),
        hypothesisText: input.trim(),
        screenerConfig,
      })
      setInput('')
      setScreenerText('')
      setStep('name')
      navigate(`/expert-networks/${project.id}/tracker`)
    } catch (error) {
      console.error('Failed to create project:', error)
    }
  }

  return (
    <div className="h-full flex flex-col items-center overflow-auto px-6 bg-white">
      {step === 'name' ? (
        <>
          {/* Hero section */}
          <div className="w-full max-w-3xl text-center mt-[10vh] mb-8 shrink-0">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-purple-600 to-indigo-600 flex items-center justify-center mx-auto mb-5">
              <Sparkles className="w-7 h-7 text-white" />
            </div>
            <h1 className="text-3xl font-semibold text-gray-900 mb-2 tracking-tight">
              Bain AI Diligence Platform
            </h1>
            <p className="text-base text-gray-500">
              Modular AI tools for every stage of due diligence — start with Expert Networks below.
            </p>
          </div>

          {/* Module cards */}
          <div className="w-full max-w-3xl mb-8 shrink-0">
            <div className="grid gap-3 sm:grid-cols-4">
              {/* Expert Networks — active */}
              <button
                onClick={() => document.getElementById('project-input')?.focus()}
                className="relative p-4 rounded-xl border-2 border-purple-300 bg-purple-50 text-left group hover:border-purple-400 transition-all"
              >
                <div className="w-9 h-9 rounded-lg bg-purple-600 flex items-center justify-center mb-3">
                  <Users className="w-5 h-5 text-white" />
                </div>
                <p className="font-semibold text-gray-900 text-sm">Expert Networks</p>
                <p className="text-xs text-gray-500 mt-1">Screen & rank experts</p>
                <span className="absolute top-3 right-3 text-[10px] font-semibold text-purple-600 bg-purple-100 px-1.5 py-0.5 rounded-full">
                  Active
                </span>
              </button>

              {/* AI Agent — active */}
              <button
                onClick={() => navigate('/agent')}
                className="relative p-4 rounded-xl border-2 border-purple-300 bg-purple-50 text-left group hover:border-purple-400 transition-all"
              >
                <div className="w-9 h-9 rounded-lg bg-purple-600 flex items-center justify-center mb-3">
                  <Bot className="w-5 h-5 text-white" />
                </div>
                <p className="font-semibold text-gray-900 text-sm">AI Agent</p>
                <p className="text-xs text-gray-500 mt-1">Search & analyze docs</p>
                <span className="absolute top-3 right-3 text-[10px] font-semibold text-purple-600 bg-purple-100 px-1.5 py-0.5 rounded-full">
                  Active
                </span>
              </button>

              {/* Coming soon modules */}
              {[
                { icon: FileText, label: 'Data Room', desc: 'Analyze documents' },
                { icon: BarChart3, label: 'Market Sizing', desc: 'Model TAM/SAM' },
              ].map(({ icon: Icon, label, desc }) => (
                <div
                  key={label}
                  className="relative p-4 rounded-xl border border-gray-100 bg-gray-50/50 text-left opacity-60"
                >
                  <div className="w-9 h-9 rounded-lg bg-gray-200 flex items-center justify-center mb-3">
                    <Icon className="w-5 h-5 text-gray-400" />
                  </div>
                  <p className="font-semibold text-gray-500 text-sm">{label}</p>
                  <p className="text-xs text-gray-400 mt-1">{desc}</p>
                  <Lock className="absolute top-3 right-3 w-3.5 h-3.5 text-gray-300" />
                </div>
              ))}
            </div>
          </div>

          {/* Input box */}
          <div className="w-full max-w-3xl mb-10 shrink-0">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-2 px-1">
              New Expert Network Project
            </p>
            <form onSubmit={handleNameSubmit}>
              <div className="relative">
                <input
                  id="project-input"
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="e.g., Pharma supply chain due diligence..."
                  className="w-full px-5 py-4 pr-14 text-base border border-gray-200 rounded-2xl shadow-sm focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent placeholder:text-gray-400 bg-gray-50"
                />
                <button
                  type="submit"
                  disabled={!input.trim()}
                  className="absolute right-2 top-1/2 -translate-y-1/2 w-10 h-10 flex items-center justify-center rounded-xl bg-purple-600 text-white hover:bg-purple-700 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                >
                  <ArrowRight className="w-5 h-5" />
                </button>
              </div>
            </form>
          </div>

          {/* Existing projects */}
          {projects.length > 0 && (
            <div className="w-full max-w-3xl pb-8">
              <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-3 px-1">
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
        </>
      ) : (
        /* Step 2: Screener Configuration */
        <div className="w-full max-w-2xl mt-[10vh] shrink-0">
          <div className="flex items-center justify-between mb-6">
            <div>
              <p className="text-sm text-gray-400 uppercase tracking-wider">New Project</p>
              <h2 className="text-2xl font-semibold text-gray-900">{input}</h2>
            </div>
            <button
              onClick={() => setStep('name')}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <X className="w-5 h-5 text-gray-400" />
            </button>
          </div>

          <div className="bg-purple-50 border border-purple-100 rounded-xl p-5 mb-6">
            <div className="flex items-center gap-2 mb-2">
              <Sparkles className="w-5 h-5 text-purple-600" />
              <h3 className="font-semibold text-purple-900">Screener Configuration</h3>
            </div>
            <p className="text-sm text-purple-700 mb-4">
              Paste your screening questions and ideal answers below. The AI will use these to assess experts. You can refine them later.
            </p>
            <textarea
              value={screenerText}
              onChange={(e) => setScreenerText(e.target.value)}
              rows={10}
              className="w-full px-4 py-3 text-sm border border-purple-200 rounded-xl bg-white focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent placeholder:text-gray-400 resize-y"
              placeholder={`Question 1: Have you led global cold-chain distribution for biologics?\nIdeal answer: Yes — direct ownership of temperature-controlled logistics across regions.\n\nQuestion 2: Experience with specialty pharma launch readiness?\nIdeal answer: Hands-on experience coordinating 3PLs, wholesalers, and demand planning.\n\nQuestion 3: Familiarity with rare-disease distribution models?\nIdeal answer: Deep experience with low-volume, high-complexity therapies.`}
            />
          </div>

          <div className="flex gap-3 justify-end">
            <button
              onClick={() => handleCreateProject(false)}
              disabled={createProject.isPending}
              className="px-5 py-2.5 text-sm font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-xl transition-colors disabled:opacity-50"
            >
              Skip for now
            </button>
            <button
              onClick={() => handleCreateProject(true)}
              disabled={createProject.isPending}
              className="px-5 py-2.5 text-sm font-medium text-white bg-purple-600 hover:bg-purple-700 rounded-xl transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              {createProject.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
              Create Project
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
