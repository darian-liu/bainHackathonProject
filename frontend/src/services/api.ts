import type { Folder, File, IngestResult, ChatResponse } from '@/types'

const API_BASE = import.meta.env.VITE_API_URL || ''

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${url}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  })
  
  if (!response.ok) {
    const error = await response.text()
    throw new Error(error || `HTTP ${response.status}`)
  }
  
  return response.json()
}

// Data Room API
export const dataRoomApi = {
  listFolders: async (parentId?: string): Promise<Folder[]> => {
    const url = parentId 
      ? `/api/data-room/folders?parent_id=${parentId}`
      : '/api/data-room/folders'
    const data = await fetchJSON<{ folders: Folder[] }>(url)
    return data.folders
  },

  listFiles: async (folderId: string): Promise<File[]> => {
    const data = await fetchJSON<{ files: File[] }>(
      `/api/data-room/folders/${folderId}/files`
    )
    return data.files
  },

  ingestFolder: async (folderId: string): Promise<IngestResult[]> => {
    const data = await fetchJSON<{ results: IngestResult[] }>(
      '/api/data-room/ingest',
      {
        method: 'POST',
        body: JSON.stringify({ folder_id: folderId }),
      }
    )
    return data.results
  },

  chat: async (message: string, sessionId?: string): Promise<ChatResponse> => {
    return fetchJSON<ChatResponse>('/api/data-room/chat', {
      method: 'POST',
      body: JSON.stringify({ message, session_id: sessionId }),
    })
  },

  clearDocuments: async (): Promise<void> => {
    await fetchJSON('/api/data-room/documents', {
      method: 'DELETE',
    })
  },
}

// Health check
export const healthCheck = async (): Promise<boolean> => {
  try {
    await fetchJSON('/health')
    return true
  } catch {
    return false
  }
}
