/**
 * API client and React Query hooks for Expert Networks module
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import type {
  Project,
  Expert,
  EmailExtractionResult,
  DedupeCandidate,
  ExpertSource,
  ScreenerConfig,
  AutoIngestResult,
  IngestionLog,
  ExpertWithDetails,
  AutoScanResult,
} from './types'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// ============== API Functions ============== //

export const expertNetworksApi = {
  // Projects
  listProjects: async (): Promise<{ projects: Project[] }> => {
    const res = await fetch(`${API_BASE}/api/expert-networks/projects`)
    if (!res.ok) throw new Error('Failed to fetch projects')
    return res.json()
  },

  createProject: async (data: {
    name: string
    hypothesisText: string
    networks?: string[]
    screenerConfig?: ScreenerConfig
  }): Promise<Project> => {
    const res = await fetch(`${API_BASE}/api/expert-networks/projects`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    if (!res.ok) throw new Error('Failed to create project')
    return res.json()
  },

  getProject: async (projectId: string): Promise<Project> => {
    const res = await fetch(
      `${API_BASE}/api/expert-networks/projects/${projectId}`
    )
    if (!res.ok) throw new Error('Failed to fetch project')
    return res.json()
  },

  updateScreenerConfig: async (
    projectId: string,
    screenerConfig: ScreenerConfig
  ): Promise<Project> => {
    const res = await fetch(
      `${API_BASE}/api/expert-networks/projects/${projectId}/screener-config`,
      {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ screenerConfig }),
      }
    )
    if (!res.ok) throw new Error('Failed to update screener config')
    return res.json()
  },

  // Email extraction
  extractEmail: async (
    projectId: string,
    emailText: string,
    network?: string
  ): Promise<EmailExtractionResult> => {
    const res = await fetch(
      `${API_BASE}/api/expert-networks/projects/${projectId}/extract`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ emailText, network }),
      }
    )
    if (!res.ok) {
      const error = await res.json()
      throw new Error(error.detail || 'Extraction failed')
    }
    return res.json()
  },

  // Commit experts (legacy manual flow)
  commitExperts: async (
    projectId: string,
    emailId: string,
    selectedIndices: number[]
  ): Promise<{ success: boolean; expertsCreated: number }> => {
    const res = await fetch(
      `${API_BASE}/api/expert-networks/projects/${projectId}/commit`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ emailId, selectedIndices }),
      }
    )
    if (!res.ok) {
      const error = await res.json()
      throw new Error(error.detail || 'Commit failed')
    }
    return res.json()
  },

  // Auto-ingest (new streamlined flow)
  autoIngest: async (
    projectId: string,
    emailText: string,
    network?: string,
    autoMergeThreshold: number = 0.85
  ): Promise<AutoIngestResult> => {
    const res = await fetch(
      `${API_BASE}/api/expert-networks/projects/${projectId}/auto-ingest`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ emailText, network, autoMergeThreshold }),
      }
    )
    if (!res.ok) {
      const error = await res.json()
      throw new Error(error.detail || 'Auto-ingest failed')
    }
    return res.json()
  },

  // NOTE: undoIngestion and redoIngestion REMOVED - they were fundamentally broken
  // Users should use explicit delete instead

  // Get latest ingestion log
  getLatestIngestionLog: async (
    projectId: string
  ): Promise<{ log: IngestionLog | null }> => {
    const res = await fetch(
      `${API_BASE}/api/expert-networks/projects/${projectId}/ingestion-logs/latest`
    )
    if (!res.ok) throw new Error('Failed to fetch ingestion log')
    return res.json()
  },

  // Screen expert
  screenExpert: async (
    expertId: string,
    projectId: string
  ): Promise<{
    grade: string
    score: number
    rationale: string
    confidence: string
    missingInfo: string[] | null
    suggestedQuestions: string[] | null
  }> => {
    const res = await fetch(
      `${API_BASE}/api/expert-networks/experts/${expertId}/screen`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ projectId }),
      }
    )
    if (!res.ok) {
      const error = await res.json()
      throw new Error(error.detail || 'Screening failed')
    }
    return res.json()
  },

  // Auto-scan Outlook inbox
  autoScanInbox: async (
    projectId: string,
    maxEmails: number = 50
  ): Promise<AutoScanResult> => {
    const res = await fetch(
      `${API_BASE}/api/expert-networks/projects/${projectId}/auto-scan-inbox`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ maxEmails }),
      }
    )
    if (!res.ok) {
      const error = await res.json()
      throw new Error(error.detail || 'Auto-scan failed')
    }
    return res.json()
  },

  // Screen all experts in project
  screenAllExperts: async (
    projectId: string,
    force: boolean = false
  ): Promise<{
    screened: number
    failed: number
    skipped: number
    results: Array<{
      expertId: string
      expertName: string
      grade?: string
      score?: number
      success: boolean
      error?: string
    }>
  }> => {
    const url = new URL(
      `${API_BASE}/api/expert-networks/projects/${projectId}/screen-all`
    )
    if (force) url.searchParams.set('force', 'true')
    const res = await fetch(url.toString(), { method: 'POST' })
    if (!res.ok) {
      const error = await res.json()
      throw new Error(error.detail || 'Batch screening failed')
    }
    return res.json()
  },

  // Experts
  listExperts: async (
    projectId: string,
    status?: string
  ): Promise<{ experts: Expert[] }> => {
    const url = new URL(
      `${API_BASE}/api/expert-networks/projects/${projectId}/experts`
    )
    if (status) url.searchParams.set('status', status)
    const res = await fetch(url.toString())
    if (!res.ok) throw new Error('Failed to fetch experts')
    return res.json()
  },

  updateExpert: async (
    expertId: string,
    updates: Partial<Expert>
  ): Promise<{ success: boolean }> => {
    const res = await fetch(
      `${API_BASE}/api/expert-networks/experts/${expertId}`,
      {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ updates }),
      }
    )
    if (!res.ok) throw new Error('Failed to update expert')
    return res.json()
  },

  getExpertSources: async (expertId: string): Promise<{ sources: ExpertSource[] }> => {
    const res = await fetch(
      `${API_BASE}/api/expert-networks/experts/${expertId}/sources`
    )
    if (!res.ok) throw new Error('Failed to fetch expert sources')
    return res.json()
  },

  // Bulk delete experts
  bulkDeleteExperts: async (
    projectId: string,
    expertIds: string[]
  ): Promise<{ success: boolean; deletedCount: number; failedCount: number }> => {
    const res = await fetch(
      `${API_BASE}/api/expert-networks/projects/${projectId}/experts/bulk-delete`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ expertIds }),
      }
    )
    if (!res.ok) {
      const error = await res.json()
      throw new Error(error.detail || 'Bulk delete failed')
    }
    return res.json()
  },

  getExpertDetails: async (expertId: string): Promise<ExpertWithDetails> => {
    const res = await fetch(
      `${API_BASE}/api/expert-networks/experts/${expertId}/details`
    )
    if (!res.ok) throw new Error('Failed to fetch expert details')
    return res.json()
  },

  recommendExpert: async (
    expertId: string,
    projectId: string
  ): Promise<{
    recommendation: string
    rationale: string
    confidence: string
  }> => {
    const res = await fetch(
      `${API_BASE}/api/expert-networks/experts/${expertId}/recommend`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ projectId }),
      }
    )
    if (!res.ok) {
      const error = await res.json()
      throw new Error(error.detail || 'Recommendation failed')
    }
    return res.json()
  },

  // Deduplication
  listDuplicates: async (
    projectId: string,
    status?: string
  ): Promise<{ candidates: DedupeCandidate[] }> => {
    const url = new URL(
      `${API_BASE}/api/expert-networks/projects/${projectId}/duplicates`
    )
    if (status) url.searchParams.set('status', status)
    const res = await fetch(url.toString())
    if (!res.ok) throw new Error('Failed to fetch duplicates')
    return res.json()
  },

  mergeDuplicates: async (candidateId: string): Promise<{ success: boolean }> => {
    const res = await fetch(
      `${API_BASE}/api/expert-networks/duplicates/${candidateId}/merge`,
      {
        method: 'POST',
      }
    )
    if (!res.ok) throw new Error('Failed to merge duplicates')
    return res.json()
  },

  markNotSame: async (candidateId: string): Promise<{ success: boolean }> => {
    const res = await fetch(
      `${API_BASE}/api/expert-networks/duplicates/${candidateId}/not-same`,
      {
        method: 'POST',
      }
    )
    if (!res.ok) throw new Error('Failed to mark as not same')
    return res.json()
  },

  // Export
  exportCSV: async (projectId: string): Promise<Blob> => {
    const res = await fetch(
      `${API_BASE}/api/expert-networks/projects/${projectId}/export`
    )
    if (!res.ok) throw new Error('Failed to export CSV')
    return res.blob()
  },
}

// ============== React Query Hooks ============== //

export function useProjects() {
  return useQuery({
    queryKey: ['expert-projects'],
    queryFn: expertNetworksApi.listProjects,
  })
}

export function useProject(projectId: string) {
  return useQuery({
    queryKey: ['expert-project', projectId],
    queryFn: () => expertNetworksApi.getProject(projectId),
    enabled: !!projectId,
  })
}

export function useCreateProject() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: expertNetworksApi.createProject,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['expert-projects'] })
    },
  })
}

export function useExtractEmail() {
  return useMutation({
    mutationFn: ({
      projectId,
      emailText,
      network,
    }: {
      projectId: string
      emailText: string
      network?: string
    }) => expertNetworksApi.extractEmail(projectId, emailText, network),
  })
}

export function useCommitExperts() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      projectId,
      emailId,
      selectedIndices,
    }: {
      projectId: string
      emailId: string
      selectedIndices: number[]
    }) => expertNetworksApi.commitExperts(projectId, emailId, selectedIndices),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ['experts', variables.projectId],
      })
      queryClient.invalidateQueries({
        queryKey: ['duplicates', variables.projectId],
      })
    },
  })
}

export function useAutoIngest() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      projectId,
      emailText,
      network,
      autoMergeThreshold,
    }: {
      projectId: string
      emailText: string
      network?: string
      autoMergeThreshold?: number
    }) => expertNetworksApi.autoIngest(projectId, emailText, network, autoMergeThreshold),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ['experts', variables.projectId],
      })
      queryClient.invalidateQueries({
        queryKey: ['duplicates', variables.projectId],
      })
      queryClient.invalidateQueries({
        queryKey: ['ingestion-log', variables.projectId],
      })
    },
  })
}

// NOTE: useUndoIngestion and useRedoIngestion REMOVED - they were fundamentally broken
// Users should use explicit delete instead

export function useBulkDeleteExperts() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      projectId,
      expertIds,
    }: {
      projectId: string
      expertIds: string[]
    }) => expertNetworksApi.bulkDeleteExperts(projectId, expertIds),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ['experts', variables.projectId],
      })
    },
  })
}

export function useLatestIngestionLog(projectId: string) {
  return useQuery({
    queryKey: ['ingestion-log', projectId],
    queryFn: () => expertNetworksApi.getLatestIngestionLog(projectId),
    enabled: !!projectId,
  })
}

export function useUpdateScreenerConfig() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      projectId,
      screenerConfig,
    }: {
      projectId: string
      screenerConfig: import('./types').ScreenerConfig
    }) => expertNetworksApi.updateScreenerConfig(projectId, screenerConfig),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ['expert-project', variables.projectId],
      })
    },
  })
}

export function useScreenExpert() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ expertId, projectId }: { expertId: string; projectId: string }) =>
      expertNetworksApi.screenExpert(expertId, projectId),
    onSuccess: (_, variables) => {
      // Invalidate only the specific project's experts to avoid stale data from other projects
      queryClient.invalidateQueries({ queryKey: ['experts', variables.projectId] })
    },
  })
}

export function useScreenAllExperts() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ projectId, force }: { projectId: string; force?: boolean }) =>
      expertNetworksApi.screenAllExperts(projectId, force),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['experts', variables.projectId] })
    },
  })
}

export function useAutoScanInbox() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ projectId, maxEmails }: { projectId: string; maxEmails?: number }) =>
      expertNetworksApi.autoScanInbox(projectId, maxEmails),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['experts', variables.projectId] })
      queryClient.invalidateQueries({ queryKey: ['duplicates', variables.projectId] })
      queryClient.invalidateQueries({ queryKey: ['ingestion-log', variables.projectId] })
    },
  })
}

export function useExperts(projectId: string, status?: string) {
  return useQuery({
    queryKey: ['experts', projectId, status],
    queryFn: () => expertNetworksApi.listExperts(projectId, status),
    enabled: !!projectId,
    staleTime: 0, // Always refetch to ensure fresh data, preventing stale cross-project contamination
  })
}

export function useUpdateExpert() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      expertId,
      updates,
      projectId,
    }: {
      expertId: string
      updates: Partial<Expert>
      projectId: string
    }) => expertNetworksApi.updateExpert(expertId, updates),
    onSuccess: (_, variables) => {
      // Invalidate only the specific project's experts to avoid stale data from other projects
      queryClient.invalidateQueries({ queryKey: ['experts', variables.projectId] })
    },
  })
}

export function useExpertSources(expertId: string) {
  return useQuery({
    queryKey: ['expert-sources', expertId],
    queryFn: () => expertNetworksApi.getExpertSources(expertId),
    enabled: !!expertId,
  })
}

export function useExpertDetails(expertId: string | null) {
  return useQuery({
    queryKey: ['expert-details', expertId],
    queryFn: () => expertNetworksApi.getExpertDetails(expertId!),
    enabled: !!expertId,
  })
}

export function useRecommendExpert() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ expertId, projectId }: { expertId: string; projectId: string }) =>
      expertNetworksApi.recommendExpert(expertId, projectId),
    onSuccess: (_, variables) => {
      // Invalidate only the specific project's experts to avoid stale data from other projects
      queryClient.invalidateQueries({ queryKey: ['experts', variables.projectId] })
    },
  })
}

export function useDuplicates(projectId: string, status?: string) {
  return useQuery({
    queryKey: ['duplicates', projectId, status],
    queryFn: () => expertNetworksApi.listDuplicates(projectId, status),
    enabled: !!projectId,
  })
}

export function useMergeDuplicates() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ candidateId, projectId }: { candidateId: string; projectId: string }) =>
      expertNetworksApi.mergeDuplicates(candidateId),
    onSuccess: (_, variables) => {
      // Invalidate only the specific project to avoid stale data from other projects
      queryClient.invalidateQueries({ queryKey: ['duplicates', variables.projectId] })
      queryClient.invalidateQueries({ queryKey: ['experts', variables.projectId] })
    },
  })
}

export function useMarkNotSame() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ candidateId, projectId }: { candidateId: string; projectId: string }) =>
      expertNetworksApi.markNotSame(candidateId),
    onSuccess: (_, variables) => {
      // Invalidate only the specific project to avoid stale data from other projects
      queryClient.invalidateQueries({ queryKey: ['duplicates', variables.projectId] })
    },
  })
}
