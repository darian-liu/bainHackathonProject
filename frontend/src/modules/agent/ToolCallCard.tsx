import { CheckCircle, XCircle, Search, FileText, List, FileEdit, BookOpen } from 'lucide-react'
import type { ToolCall } from '@/stores/agentStore'

interface ToolCallCardProps {
  toolCall: ToolCall
}

const toolIcons: Record<string, typeof Search> = {
  search_documents: Search,
  read_document: FileText,
  list_documents: List,
  write_document: FileEdit,
  summarize_documents: BookOpen,
}

export function ToolCallCard({ toolCall }: ToolCallCardProps) {
  const Icon = toolIcons[toolCall.name] || FileText
  const isSuccess = toolCall.result?.success

  return (
    <div className="bg-white/50 rounded border border-gray-200 p-2 text-sm">
      <div className="flex items-center gap-2">
        <Icon className="w-3 h-3 text-gray-500" />
        <span className="font-medium text-gray-700">{formatToolName(toolCall.name)}</span>
        {toolCall.result !== undefined && (
          isSuccess ? (
            <CheckCircle className="w-3 h-3 text-green-500 ml-auto" />
          ) : (
            <XCircle className="w-3 h-3 text-red-500 ml-auto" />
          )
        )}
      </div>

      {/* Show arguments */}
      {Object.keys(toolCall.arguments).length > 0 && (
        <div className="mt-1 text-xs text-gray-500">
          {formatArguments(toolCall.arguments)}
        </div>
      )}
    </div>
  )
}

function formatToolName(name: string): string {
  return name
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

function formatArguments(args: Record<string, unknown>): string {
  const parts: string[] = []

  for (const [key, value] of Object.entries(args)) {
    if (typeof value === 'string') {
      // Truncate long strings
      const displayValue = value.length > 50 ? value.slice(0, 47) + '...' : value
      parts.push(`${key}: "${displayValue}"`)
    } else if (Array.isArray(value)) {
      parts.push(`${key}: [${value.length} items]`)
    } else if (typeof value === 'number') {
      parts.push(`${key}: ${value}`)
    }
  }

  return parts.join(', ')
}
