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

  // Commit experts
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

  recommendExpert: async (
    expertId: string,
    projectId: string,
    includeDocumentContext: boolean = false
  ): Promise<{
    recommendation: string
    rationale: string
    confidence: string
    // Enhanced fields when document context is enabled
    background_fit_score?: number
    screener_quality_score?: number
    document_relevance_score?: number
    red_flags_score?: number
    overall_score?: number
    relevant_documents?: Array<{
      filename: string
      relevance_score: number
      matched_topics: string[]
    }>
  }> => {
    const res = await fetch(
      `${API_BASE}/api/expert-networks/experts/${expertId}/recommend`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          projectId,
          include_document_context: includeDocumentContext,
        }),
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

export function useExperts(projectId: string, status?: string) {
  return useQuery({
    queryKey: ['experts', projectId, status],
    queryFn: () => expertNetworksApi.listExperts(projectId, status),
    enabled: !!projectId,
  })
}

export function useUpdateExpert() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      expertId,
      updates,
    }: {
      expertId: string
      updates: Partial<Expert>
    }) => expertNetworksApi.updateExpert(expertId, updates),
    onSuccess: (_, variables) => {
      // Invalidate all expert queries to refresh the list
      queryClient.invalidateQueries({ queryKey: ['experts'] })
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

export function useRecommendExpert() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      expertId,
      projectId,
      includeDocumentContext = false,
    }: {
      expertId: string
      projectId: string
      includeDocumentContext?: boolean
    }) => expertNetworksApi.recommendExpert(expertId, projectId, includeDocumentContext),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['experts'] })
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
    mutationFn: (candidateId: string) =>
      expertNetworksApi.mergeDuplicates(candidateId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['duplicates'] })
      queryClient.invalidateQueries({ queryKey: ['experts'] })
    },
  })
}

export function useMarkNotSame() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (candidateId: string) => expertNetworksApi.markNotSame(candidateId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['duplicates'] })
    },
  })
}
