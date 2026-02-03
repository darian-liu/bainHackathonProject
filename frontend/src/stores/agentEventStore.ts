import { create } from 'zustand'
import type { AgentEvent } from '@/components/agent-visualizer/types'

interface AgentEventStore {
  events: AgentEvent[]
  addEvent: (event: AgentEvent) => void
  clearEvents: () => void
}

export const useAgentEventStore = create<AgentEventStore>((set) => ({
  events: [],
  addEvent: (event) => set((state) => ({ 
    events: [...state.events, event] 
  })),
  clearEvents: () => set({ events: [] }),
}))
