import { User, Bot, FileText } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { ChatMessage } from '@/types'

interface MessageBubbleProps {
  message: ChatMessage
  onSourceClick?: () => void
}

export function MessageBubble({ message, onSourceClick }: MessageBubbleProps) {
  const isUser = message.role === 'user'
  const hasSources = message.sources && message.sources.length > 0

  return (
    <div
      className={cn(
        'flex gap-3',
        isUser ? 'flex-row-reverse' : 'flex-row'
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          'w-8 h-8 rounded-full flex items-center justify-center shrink-0',
          isUser ? 'bg-primary' : 'bg-slate-200'
        )}
      >
        {isUser ? (
          <User className="w-4 h-4 text-primary-foreground" />
        ) : (
          <Bot className="w-4 h-4 text-slate-600" />
        )}
      </div>

      {/* Message content */}
      <div
        className={cn(
          'max-w-[80%] rounded-lg px-4 py-2',
          isUser
            ? 'bg-primary text-primary-foreground'
            : 'bg-slate-100 text-slate-900'
        )}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>
        
        {/* Sources indicator */}
        {hasSources && (
          <button
            onClick={onSourceClick}
            className="flex items-center gap-1 mt-2 text-xs opacity-70 hover:opacity-100 transition-opacity"
          >
            <FileText className="w-3 h-3" />
            <span>{message.sources!.length} source(s) cited</span>
          </button>
        )}
      </div>
    </div>
  )
}
