import { useState } from 'react'
import { ChevronLeft, ChevronRight, Trash2 } from 'lucide-react'
import { AgentFlowGraph } from './AgentFlowGraph'
import { useAgentEventStore } from '@/stores/agentEventStore'
import { useAgentEvents } from '@/hooks/useAgentEvents'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

export function AgentVisualizerSidebar() {
  const [isOpen, setIsOpen] = useState(true)
  const clearEvents = useAgentEventStore((s) => s.clearEvents)
  const eventCount = useAgentEventStore((s) => s.events.length)
  
  // Subscribe to WebSocket events
  useAgentEvents()
  
  return (
    <div className={cn(
      'relative border-l border-slate-200 bg-white transition-all duration-300',
      isOpen ? 'w-[400px]' : 'w-0'
    )}>
      {/* Toggle button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="absolute -left-8 top-4 bg-white border border-slate-200 rounded-l-md p-1 hover:bg-slate-50"
      >
        {isOpen ? <ChevronRight className="w-5 h-5" /> : <ChevronLeft className="w-5 h-5" />}
      </button>
      
      {isOpen && (
        <div className="h-full flex flex-col">
          <div className="flex items-center justify-between p-4 border-b">
            <h2 className="font-semibold">Agent Actions</h2>
            <div className="flex items-center gap-2">
              <span className="text-sm text-slate-500">{eventCount} events</span>
              <Button
                variant="ghost"
                size="sm"
                onClick={clearEvents}
                disabled={eventCount === 0}
              >
                <Trash2 className="w-4 h-4" />
              </Button>
            </div>
          </div>
          
          <div className="flex-1">
            <AgentFlowGraph />
          </div>
        </div>
      )}
    </div>
  )
}
