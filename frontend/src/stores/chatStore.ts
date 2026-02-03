import { create } from 'zustand'
import type { ChatMessage, SourceDocument } from '@/types'

interface ChatStore {
  messages: ChatMessage[]
  isLoading: boolean
  selectedSources: SourceDocument[]
  
  addMessage: (message: Omit<ChatMessage, 'id' | 'timestamp'>) => void
  updateLastMessage: (content: string, sources?: SourceDocument[]) => void
  setLoading: (loading: boolean) => void
  setSelectedSources: (sources: SourceDocument[]) => void
  clearMessages: () => void
}

export const useChatStore = create<ChatStore>((set) => ({
  messages: [],
  isLoading: false,
  selectedSources: [],

  addMessage: (message) => set((state) => ({
    messages: [
      ...state.messages,
      {
        ...message,
        id: crypto.randomUUID(),
        timestamp: new Date(),
      },
    ],
  })),

  updateLastMessage: (content, sources) => set((state) => {
    const messages = [...state.messages]
    if (messages.length > 0) {
      const lastMessage = messages[messages.length - 1]
      messages[messages.length - 1] = {
        ...lastMessage,
        content,
        sources: sources || lastMessage.sources,
      }
    }
    return { messages }
  }),

  setLoading: (isLoading) => set({ isLoading }),

  setSelectedSources: (selectedSources) => set({ selectedSources }),

  clearMessages: () => set({ messages: [], selectedSources: [] }),
}))
