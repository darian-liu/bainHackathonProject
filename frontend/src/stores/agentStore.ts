import { create } from 'zustand'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export interface ToolCall {
  id: string
  name: string
  arguments: Record<string, unknown>
  result?: { success: boolean }
}

export interface AgentMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  toolCalls?: ToolCall[]
  timestamp: Date
}

export interface ToolInfo {
  name: string
  description: string
  parameters: Record<string, unknown>
}

export interface UploadedFile {
  file_id: string
  filename: string
  chunks: number
}

interface AgentStore {
  messages: AgentMessage[]
  isProcessing: boolean
  sessionId: string
  projectId: string | null
  error: string | null
  availableTools: ToolInfo[]
  uploadedFiles: UploadedFile[]

  sendMessage: (content: string) => Promise<void>
  clearMessages: () => Promise<void>
  loadTools: () => Promise<void>
  loadUploadedFiles: () => Promise<void>
  addUploadedFile: (file: UploadedFile) => void
  removeUploadedFile: (fileId: string) => void
  setSessionId: (sessionId: string) => void
  setProjectId: (projectId: string | null) => void
  clearError: () => void
}

export const useAgentStore = create<AgentStore>((set, get) => ({
  messages: [],
  isProcessing: false,
  sessionId: 'default',
  projectId: null,
  error: null,
  availableTools: [],
  uploadedFiles: [],

  sendMessage: async (content: string) => {
    const { sessionId, projectId } = get()

    // Add user message immediately
    const userMessage: AgentMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content,
      timestamp: new Date(),
    }

    set((state) => ({
      messages: [...state.messages, userMessage],
      isProcessing: true,
      error: null,
    }))

    try {
      const res = await fetch(`${API_BASE}/api/agent/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: content,
          session_id: sessionId,
          project_id: projectId,
        }),
      })

      if (!res.ok) {
        const error = await res.json()
        throw new Error(error.detail || 'Chat failed')
      }

      const data = await res.json()

      // Add assistant message
      const assistantMessage: AgentMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: data.response,
        toolCalls: data.tool_calls,
        timestamp: new Date(),
      }

      set((state) => ({
        messages: [...state.messages, assistantMessage],
        isProcessing: false,
      }))
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to send message',
        isProcessing: false,
      })
    }
  },

  clearMessages: async () => {
    const { sessionId } = get()

    try {
      await fetch(`${API_BASE}/api/agent/clear?session_id=${sessionId}`, {
        method: 'POST',
      })

      set({ messages: [], error: null })
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to clear messages',
      })
    }
  },

  loadTools: async () => {
    // Tools are handled internally by the agent, no need to fetch them
    set({ availableTools: [] })
  },

  loadUploadedFiles: async () => {
    try {
      const res = await fetch(`${API_BASE}/api/agent/documents`)
      if (res.ok) {
        const data = await res.json()
        set({ uploadedFiles: data.files || [] })
      }
    } catch {
      // Silently fail — files list is non-critical
    }
  },

  addUploadedFile: (file: UploadedFile) => {
    set((state) => ({
      uploadedFiles: [...state.uploadedFiles.filter(f => f.file_id !== file.file_id), file],
    }))
  },

  removeUploadedFile: (fileId: string) => {
    set((state) => ({
      uploadedFiles: state.uploadedFiles.filter(f => f.file_id !== fileId),
    }))
  },

  setSessionId: (sessionId: string) => set({ sessionId }),

  setProjectId: (projectId: string | null) => set({ projectId }),

  clearError: () => set({ error: null }),
}))

// API helper for file uploads
export async function uploadDocument(file: File, sessionId: string = 'default'): Promise<{
  success: boolean
  filename: string
  file_id?: string
  chunks?: number
  error?: string
}> {
  const formData = new FormData()
  formData.append('file', file)

  const res = await fetch(`${API_BASE}/api/agent/upload?session_id=${sessionId}`, {
    method: 'POST',
    body: formData,
  })

  if (!res.ok) {
    const error = await res.json()
    throw new Error(error.detail || 'Upload failed')
  }

  return res.json()
}
