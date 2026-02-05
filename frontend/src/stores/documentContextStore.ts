import { create } from 'zustand'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export interface DocumentInfo {
  file_id: string
  filename: string
  folder_id: string | null
  chunk_count: number
}

export interface SearchResult {
  text: string
  score: number
  filename: string
  file_id: string
  chunk_index: number
  folder_id: string | null
}

interface DocumentContextStore {
  documents: DocumentInfo[]
  isLoaded: boolean
  isLoading: boolean
  error: string | null

  loadDocuments: () => Promise<void>
  searchDocuments: (query: string, nResults?: number) => Promise<SearchResult[]>
  getContextSummary: () => Promise<string>
  clearError: () => void
}

export const useDocumentContextStore = create<DocumentContextStore>((set, get) => ({
  documents: [],
  isLoaded: false,
  isLoading: false,
  error: null,

  loadDocuments: async () => {
    if (get().isLoading) return

    set({ isLoading: true, error: null })

    try {
      const res = await fetch(`${API_BASE}/api/document-context/documents`)
      if (!res.ok) {
        throw new Error('Failed to load documents')
      }
      const data = await res.json()
      set({
        documents: data.documents || [],
        isLoaded: true,
        isLoading: false,
      })
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to load documents',
        isLoading: false,
      })
    }
  },

  searchDocuments: async (query: string, nResults: number = 5): Promise<SearchResult[]> => {
    try {
      const res = await fetch(`${API_BASE}/api/document-context/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, n_results: nResults }),
      })

      if (!res.ok) {
        throw new Error('Search failed')
      }

      const data = await res.json()
      return data.results || []
    } catch (error) {
      set({ error: error instanceof Error ? error.message : 'Search failed' })
      return []
    }
  },

  getContextSummary: async (): Promise<string> => {
    try {
      const res = await fetch(`${API_BASE}/api/document-context/summary`)
      if (!res.ok) {
        throw new Error('Failed to get context summary')
      }
      const data = await res.json()
      return data.summary || ''
    } catch (error) {
      set({ error: error instanceof Error ? error.message : 'Failed to get summary' })
      return ''
    }
  },

  clearError: () => set({ error: null }),
}))
