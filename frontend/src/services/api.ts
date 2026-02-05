import type { Folder, File, IngestResult, ChatResponse } from '@/types'

const API_BASE = import.meta.env.VITE_API_URL || ''

interface ApiError {
  message: string
  status: number
}

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${url}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  })

  if (!response.ok) {
    const errorText = await response.text()
    const error: ApiError = {
      message: errorText || `HTTP ${response.status}`,
      status: response.status,
    }
    throw error
  }

  return response.json() as Promise<T>
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
    await fetchJSON<{ status: string }>('/api/data-room/documents', {
      method: 'DELETE',
    })
  },
}

// Settings types
export interface SettingsData {
  document_source_mode: string
  openai_api_key: string
  openai_base_url: string
  openai_model: string
  graph_client_id: string
  graph_client_secret: string
  graph_tenant_id: string
  sharepoint_site_id: string
  // Personal Outlook Integration
  outlook_client_id: string
  outlook_client_secret: string
  outlook_redirect_uri: string
  outlook_allowed_sender_domains: string
  outlook_network_keywords: string
}

export interface TestConnectionResult {
  openai: boolean
  sharepoint: boolean | null
  errors: Record<string, string>
}

// Settings API
export const settingsApi = {
  getSettings: async (): Promise<SettingsData> => {
    return fetchJSON<SettingsData>('/api/settings')
  },

  updateSettings: async (settings: Partial<SettingsData>): Promise<SettingsData> => {
    return fetchJSON<SettingsData>('/api/settings', {
      method: 'POST',
      body: JSON.stringify(settings),
    })
  },

  testConnections: async (): Promise<TestConnectionResult> => {
    return fetchJSON<TestConnectionResult>('/api/settings/test', {
      method: 'POST',
    })
  },
}

// Outlook types
export interface OutlookStatus {
  connected: boolean
  userEmail: string | null
  lastConnectedAt: string | null
  lastTestAt: string | null
  lastSyncAt: string | null
}

export interface OutlookTestResult {
  success: boolean
  userEmail: string | null
  error: string | null
}

export interface OutlookAuthUrl {
  authUrl: string
}

// Outlook API
export const outlookApi = {
  getStatus: async (): Promise<OutlookStatus> => {
    return fetchJSON<OutlookStatus>('/api/outlook/status')
  },

  getAuthUrl: async (returnPath: string = '/settings'): Promise<OutlookAuthUrl> => {
    return fetchJSON<OutlookAuthUrl>(`/api/outlook/auth-url?return_path=${encodeURIComponent(returnPath)}`)
  },

  testConnection: async (): Promise<OutlookTestResult> => {
    return fetchJSON<OutlookTestResult>('/api/outlook/test', {
      method: 'POST',
    })
  },

  disconnect: async (): Promise<{ success: boolean; message: string }> => {
    return fetchJSON<{ success: boolean; message: string }>('/api/outlook/disconnect', {
      method: 'POST',
    })
  },
}

// Health check
export const healthCheck = async (): Promise<boolean> => {
  try {
    await fetchJSON<{ status: string }>('/health')
    return true
  } catch {
    return false
  }
}
