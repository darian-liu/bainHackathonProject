/**
 * TypeScript types for Expert Networks module
 */

export interface Project {
  id: string
  name: string
  hypothesisText: string
  networks: string[] | null
  createdAt: string
  updatedAt: string
}

export interface Expert {
  id: string
  projectId: string
  canonicalName: string
  canonicalEmployer: string | null
  canonicalTitle: string | null
  status: ExpertStatus
  statusUpdatedAt: string
  conflictStatus: ConflictStatus | null
  conflictId: string | null
  interviewDate: string | null
  leadInterviewer: string | null
  interviewLength: number | null
  hypothesisNotes: string | null
  hypothesisMatch: HypothesisMatch | null
  aiRecommendation: AIRecommendation | null
  aiRecommendationRationale: string | null
  aiRecommendationConfidence: Confidence | null
  createdAt: string
  updatedAt: string
}

export type ExpertStatus =
  | 'recommended'
  | 'awaiting_screeners'
  | 'screened_out'
  | 'shortlisted'
  | 'requested'
  | 'scheduled'
  | 'completed'
  | 'unresponsive'
  | 'conflict'
  | 'declined'

export type ConflictStatus = 'cleared' | 'pending' | 'conflict'

export type HypothesisMatch = 'yes' | 'no' | 'unknown'

export type AIRecommendation = 'strong_fit' | 'maybe' | 'low_fit'

export type Confidence = 'low' | 'medium' | 'high'

export interface FieldProvenance {
  excerptText: string
  charStart?: number
  charEnd?: number
  confidence: Confidence
}

export interface ExtractedExpert {
  fullName: string
  fullNameProvenance: FieldProvenance
  employer: string | null
  employerProvenance: FieldProvenance | null
  title: string | null
  titleProvenance: FieldProvenance | null
  relevanceBullets: string[] | null
  relevanceBulletsProvenance: FieldProvenance | null
  screenerResponses: ScreenerResponse[] | null
  screenerResponsesProvenance: FieldProvenance | null
  conflictStatus: ConflictStatus | null
  conflictId: string | null
  conflictProvenance: FieldProvenance | null
  availabilityWindows: string[] | null
  availabilityProvenance: FieldProvenance | null
  statusCue: StatusCue | null
  statusCueProvenance: FieldProvenance | null
  overallConfidence: Confidence
}

export interface ScreenerResponse {
  question?: string
  answer: string
}

export type StatusCue =
  | 'available'
  | 'declined'
  | 'conflict'
  | 'not_a_fit'
  | 'no_longer_available'
  | 'pending'
  | 'interested'
  | 'unknown'

export interface EmailExtractionResult {
  emailId: string
  result: {
    inferredNetwork: string | null
    networkConfidence: Confidence | null
    emailDate: string | null
    experts: ExtractedExpert[]
    extractionNotes: string[] | null
  }
}

export interface DedupeCandidate {
  id: string
  projectId: string
  expertIdA: string
  expertIdB: string
  expertAName: string
  expertAEmployer: string | null
  expertBName: string
  expertBEmployer: string | null
  score: number
  matchType: 'strong_name_employer' | 'medium_name_roles' | 'fuzzy_name_employer'
  status: 'pending' | 'merged' | 'not_same'
  createdAt: string
  resolvedAt: string | null
}

export interface ExpertSource {
  id: string
  expertId: string
  emailId: string
  network: string | null
  extractedJson: string
  extractedName: string | null
  extractedEmployer: string | null
  extractedTitle: string | null
  extractedBio: string | null
  extractedScreener: string | null
  extractedAvailability: string | null
  extractedStatusCue: string | null
  createdAt: string
  // From email join
  rawText?: string
}
