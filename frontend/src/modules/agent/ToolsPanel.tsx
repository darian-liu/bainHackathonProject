import { Search, FileText, List, FileEdit, BookOpen } from 'lucide-react'
import type { ToolInfo } from '@/stores/agentStore'

interface ToolsPanelProps {
  tools: ToolInfo[]
}

const toolIcons: Record<string, typeof Search> = {
  search_documents: Search,
  read_document: FileText,
  list_documents: List,
  write_document: FileEdit,
  summarize_documents: BookOpen,
}

export function ToolsPanel({ tools }: ToolsPanelProps) {
  if (tools.length === 0) {
    return (
      <div className="p-4 text-center text-gray-500 text-sm">
        Loading tools...
      </div>
    )
  }

  return (
    <div className="p-4 space-y-3">
      {tools.map((tool) => {
        const Icon = toolIcons[tool.name] || FileText

        return (
          <div
            key={tool.name}
            className="p-3 bg-gray-50 rounded-lg border border-gray-100"
          >
            <div className="flex items-center gap-2 mb-1">
              <Icon className="w-4 h-4 text-gray-500" />
              <span className="font-medium text-sm text-gray-700">
                {formatToolName(tool.name)}
              </span>
            </div>
            <p className="text-xs text-gray-500">{tool.description}</p>
          </div>
        )
      })}
    </div>
  )
}

function formatToolName(name: string): string {
  return name
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}
