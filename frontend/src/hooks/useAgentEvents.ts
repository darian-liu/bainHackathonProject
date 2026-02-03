import { useEffect, useRef } from 'react'
import { useAgentEventStore } from '@/stores/agentEventStore'
import type { AgentEvent } from '@/components/agent-visualizer/types'

export function useAgentEvents() {
  const wsRef = useRef<WebSocket | null>(null)
  const addEvent = useAgentEventStore((s) => s.addEvent)
  
  useEffect(() => {
    const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws'
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws
    
    ws.onmessage = (event) => {
      try {
        const agentEvent: AgentEvent = JSON.parse(event.data)
        addEvent(agentEvent)
      } catch (e) {
        console.error('Failed to parse agent event:', e)
      }
    }
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }
    
    return () => {
      ws.close()
    }
  }, [addEvent])
  
  return wsRef.current
}
