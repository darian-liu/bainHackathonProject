import { memo } from 'react'
import { Handle, Position, type NodeProps } from 'reactflow'
import { cn } from '@/lib/utils'
import { 
  Play, 
  Wrench, 
  MessageSquare, 
  MessageCircle, 
  CheckCircle 
} from 'lucide-react'
import type { EventNodeData, EventType } from './types'

const eventConfig: Record<EventType, { 
  bg: string
  border: string
  icon: React.ElementType
  label: string
}> = {
  agent_started: { 
    bg: 'bg-green-50', 
    border: 'border-green-500',
    icon: Play,
    label: 'Started'
  },
  tool_called: { 
    bg: 'bg-blue-50', 
    border: 'border-blue-500',
    icon: Wrench,
    label: 'Tool Call'
  },
  llm_request: { 
    bg: 'bg-purple-50', 
    border: 'border-purple-500',
    icon: MessageSquare,
    label: 'LLM Request'
  },
  llm_response: { 
    bg: 'bg-indigo-50', 
    border: 'border-indigo-500',
    icon: MessageCircle,
    label: 'LLM Response'
  },
  agent_completed: { 
    bg: 'bg-gray-50', 
    border: 'border-gray-500',
    icon: CheckCircle,
    label: 'Completed'
  },
}

export const EventNode = memo(function EventNode({ 
  data 
}: NodeProps<EventNodeData>) {
  const { event } = data
  const config = eventConfig[event.type] || eventConfig.agent_started
  const Icon = config.icon
  
  return (
    <div className={cn(
      'px-4 py-3 rounded-lg border-2 shadow-sm min-w-[180px]',
      config.bg,
      config.border
    )}>
      <Handle 
        type="target" 
        position={Position.Top} 
        className="!bg-slate-400"
      />
      
      <div className="flex items-center gap-2">
        <Icon className="w-4 h-4" />
        <span className="font-medium text-sm">{config.label}</span>
      </div>
      
      <div className="text-xs text-slate-500 mt-1">
        {new Date(event.timestamp).toLocaleTimeString()}
      </div>
      
      {event.data && Object.keys(event.data).length > 0 && (
        <div className="text-xs text-slate-600 mt-2 max-w-[200px] truncate">
          {JSON.stringify(event.data)}
        </div>
      )}
      
      <Handle 
        type="source" 
        position={Position.Bottom}
        className="!bg-slate-400"
      />
    </div>
  )
})
