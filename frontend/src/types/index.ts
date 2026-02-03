// Shared types

export interface Folder {
  id: string
  name: string
  path: string
}

export interface File {
  id: string
  name: string
  path: string
  mime_type: string
  size: number
}

export interface IngestResult {
  file: string
  status: 'success' | 'skipped' | 'error'
  chunks?: number
  reason?: string
  error?: string
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: SourceDocument[]
  timestamp: Date
}

export interface SourceDocument {
  file_id: string
  filename: string
  chunk_index: number
  folder_id: string
}

export interface ChatResponse {
  response: string
  sources: SourceDocument[]
}
