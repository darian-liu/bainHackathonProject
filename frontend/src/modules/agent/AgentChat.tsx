import { useState, useRef, useEffect } from 'react'
import { Send, Loader2, Trash2, Wrench, Download } from 'lucide-react'
import { useAgentStore, type AgentMessage } from '@/stores/agentStore'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { ToolCallCard } from './ToolCallCard'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

interface AgentChatProps {
  onToggleTools: () => void
}

export function AgentChat({ onToggleTools }: AgentChatProps) {
  const [input, setInput] = useState('')
  const scrollRef = useRef<HTMLDivElement>(null)

  const { messages, isProcessing, sendMessage, clearMessages, error, clearError } =
    useAgentStore()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isProcessing) return

    const message = input
    setInput('')
    await sendMessage(message)
  }

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  // Clear error after showing
  useEffect(() => {
    if (error) {
      const timer = setTimeout(clearError, 5000)
      return () => clearTimeout(timer)
    }
  }, [error, clearError])

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b">
        <div>
          <h2 className="font-semibold text-lg">AI Document Agent</h2>
          <p className="text-sm text-muted-foreground">
            Ask questions, search documents, or request analysis
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={onToggleTools}>
            <Wrench className="w-4 h-4 mr-2" />
            Tools
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={clearMessages}
            disabled={messages.length === 0}
          >
            <Trash2 className="w-4 h-4 mr-2" />
            Clear
          </Button>
        </div>
      </div>

      {/* Error banner */}
      {error && (
        <div className="px-6 py-2 bg-red-50 border-b border-red-200 text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* Messages */}
      <ScrollArea className="flex-1 px-6" ref={scrollRef}>
        <div className="py-4 space-y-4">
          {messages.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-muted-foreground mb-4">
                Start a conversation with the AI agent.
              </p>
              <div className="text-sm text-gray-500 space-y-1">
                <p>Try asking:</p>
                <p className="text-gray-600">"What documents are available?"</p>
                <p className="text-gray-600">"Search for information about X"</p>
                <p className="text-gray-600">"Summarize the key findings"</p>
              </div>
            </div>
          ) : (
            messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))
          )}

          {isProcessing && (
            <div className="flex items-center gap-2 text-muted-foreground">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Agent is working...</span>
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-4 border-t">
        <div className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask the agent to analyze documents, search for info..."
            disabled={isProcessing}
            className="flex-1"
          />
          <Button type="submit" disabled={isProcessing || !input.trim()}>
            <Send className="w-4 h-4" />
          </Button>
        </div>
      </form>
    </div>
  )
}

/**
 * Parse message content and replace sandbox download links with clickable buttons.
 * Matches patterns like: [Download the document](sandbox:/agent_outputs/filename.md)
 */
function renderMessageContent(content: string) {
  // Regex to match markdown links with sandbox: URLs
  const linkRegex = /\[([^\]]+)\]\(sandbox:\/?(agent_outputs\/)?([^)]+)\)/g

  const parts: (string | JSX.Element)[] = []
  let lastIndex = 0
  let match

  while ((match = linkRegex.exec(content)) !== null) {
    // Add text before the match
    if (match.index > lastIndex) {
      parts.push(content.slice(lastIndex, match.index))
    }

    const linkText = match[1]
    const filename = match[3]

    // Add download button
    parts.push(
      <a
        key={match.index}
        href={`${API_BASE}/api/agent/download/${encodeURIComponent(filename)}`}
        download={filename}
        className="inline-flex items-center gap-1 px-2 py-1 text-sm bg-primary/10 hover:bg-primary/20 text-primary rounded transition-colors"
      >
        <Download className="w-3 h-3" />
        {linkText}
      </a>
    )

    lastIndex = match.index + match[0].length
  }

  // Add remaining text
  if (lastIndex < content.length) {
    parts.push(content.slice(lastIndex))
  }

  // If no links found, return original content
  if (parts.length === 0) {
    return content
  }

  return parts
}

function MessageBubble({ message }: { message: AgentMessage }) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[80%] rounded-lg px-4 py-2 ${isUser
            ? 'bg-primary text-primary-foreground'
            : 'bg-muted'
          }`}
      >
        <div className="whitespace-pre-wrap">{isUser ? message.content : renderMessageContent(message.content)}</div>

        {/* Show tool calls for assistant messages */}
        {!isUser && message.toolCalls && message.toolCalls.length > 0 && (
          <div className="mt-3 space-y-2">
            <div className="text-xs opacity-70 font-medium">Tools used:</div>
            {message.toolCalls.map((toolCall) => (
              <ToolCallCard key={toolCall.id} toolCall={toolCall} />
            ))}
          </div>
        )}

        <div
          className={`text-xs mt-1 ${isUser ? 'text-primary-foreground/70' : 'text-muted-foreground'
            }`}
        >
          {message.timestamp.toLocaleTimeString()}
        </div>
      </div>
    </div>
  )
}
