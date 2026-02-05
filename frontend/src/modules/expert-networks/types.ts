/**
 * TypeScript types for Expert Networks module
 */

export interface ScreenerQuestion {
  id: string
  order: number
  text: string
  idealAnswer?: string
  rubricNotes?: string
  redFlags?: string
}

export interface ScreenerConfig {
  questions: ScreenerQuestion[]
  autoScreen?: boolean  // If true, automatically screen experts after ingestion
}

export interface Project {
  id: string
  name: string
  hypothesisText: string
  networks: string[] | null
  screenerConfig: ScreenerConfig | null
  createdAt: string
  updatedAt: string
}

export interface Expert {
  id: string
  projectId: string
  canonicalName: string
  canonicalEmployer: string | null
  canonicalTitle: string | null
  network: string | null  // Expert network source (e.g., alphasights, guidepoint)
  status: ExpertStatus
  statusUpdatedAt: string
  conflictStatus: ConflictStatus | null
  conflictId: string | null
  interviewDate: string | null
  leadInterviewer: string | null
  interviewLength: number | null
  hypothesisNotes: string | null
  hypothesisMatch: HypothesisMatch | null
  // Legacy AI recommendation (deprecated, kept for backward compat)
  aiRecommendation: AIRecommendation | null
  aiRecommendationRationale: string | null
  aiRecommendationConfidence: Confidence | null
  // New Smart Screening fields
  aiScreeningGrade: ScreeningGrade | null
  aiScreeningScore: number | null
  aiScreeningRationale: string | null
  aiScreeningConfidence: Confidence | null
  aiScreeningMissingInfo: string | null // JSON array
  createdAt: string
  updatedAt: string
}

export type ScreeningGrade = 'strong' | 'mixed' | 'weak'

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

// Auto-ingestion types
export interface IngestionSummary {
  addedCount: number
  updatedCount: number
  mergedCount: number
  needsReviewCount: number
  extractedCount: number
  network: string | null
  extractionNotes: string[] | null
  isNoOp?: boolean  // True if this ingestion resulted in no changes
}

export interface IngestionChange {
  expertId?: string
  expertName?: string
  fieldsUpdated?: string[]
  keptExpertId?: string
  mergedExpertId?: string
  score?: number
  matchType?: string
  candidateId?: string
  reason?: string
}

export interface IngestionChanges {
  added: IngestionChange[]
  updated: IngestionChange[]
  merged: IngestionChange[]
  needsReview: IngestionChange[]
}

export interface AutoIngestResult {
  ingestionLogId: string
  emailId: string
  summary: IngestionSummary
  changes: IngestionChanges
}

export interface IngestionLogEntry {
  id: string
  action: 'added' | 'updated' | 'merged' | 'needs_review'
  expertId: string | null
  expertName: string | null
  mergedFromExpertId: string | null
  fieldsChanged: string[] | null
  previousValues: Record<string, unknown> | null
  newValues: Record<string, unknown> | null
  createdAt: string
}

export interface IngestionLog {
  id: string
  projectId: string
  emailId: string
  status: 'completed' | 'undone'
  summary: IngestionSummary
  entries?: IngestionLogEntry[]
  createdAt: string
  undoneAt: string | null
}

// Expert detail types for provenance/source traceability
export interface SourceFieldProvenance {
  id: string
  expertSourceId: string
  fieldName: string
  extractedValue: string
  excerptText: string | null
  charStart: number | null
  charEnd: number | null
  confidence: Confidence
  createdAt: string
}

export interface SourceWithProvenance extends ExpertSource {
  provenance: SourceFieldProvenance[]
  email_date?: string
  email_network?: string
  email_raw_text?: string
}

export interface UserEdit {
  id: string
  expertId: string
  fieldName: string
  userValueJson: string
  previousValueJson: string | null
  createdAt: string
}

export interface ExpertWithDetails extends Expert {
  sources: SourceWithProvenance[]
  userEdits: UserEdit[]
}

// Auto-scan inbox result
export interface AutoScanProgress {
  stage: string
  totalEmails: number
  processedEmails: number
  filteredEmails: number
  ingestedCount: number
  skippedCount: number
  errorCount: number
  errors: string[]
  skippedReasons?: Array<{
    messageId: string
    subject: string
    reason: string
  }>
  processedDetails?: Array<{
    messageId: string
    subject: string
    sender: string
    network: string | null
    extractedCount: number
    addedCount: number
    updatedCount: number
    addedExperts: string[]
    updatedExperts: string[]
  }>
}

export interface AutoScanResult {
  status: 'scanning' | 'complete' | 'error'
  progress: AutoScanProgress
  ingestionLogId: string | null
  scanRunId: string | null
  results: {
    summary: IngestionSummary & {
      emailsProcessed: number
      emailsSkipped: number
      source?: string
    }
    changes: IngestionChanges
  }
  message: string
}

// ScanRun - persistent record of each auto-scan execution
export interface ScanRun {
  id: string
  projectId: string
  startedAt: string
  completedAt: string | null
  status: 'running' | 'completed' | 'failed'
  maxEmails: number
  messagesFetched: number
  messagesFiltered: number
  messagesAlreadyScanned: number
  messagesProcessed: number
  messagesSkipped: number
  messagesFailed: number
  expertsAdded: number
  expertsUpdated: number
  expertsMerged: number
  addedExperts: Array<{ expertId: string; expertName: string }>
  updatedExperts: Array<{ expertId: string; expertName: string; fieldsUpdated?: string[] }>
  skippedReasons: Array<{ messageId: string; subject: string; reason: string }>
  errors: string[]
  processedDetails: Array<{
    messageId: string
    subject: string
    sender: string
    network: string | null
    extractedCount: number
    addedCount: number
    updatedCount: number
  }>
  ingestionLogId: string | null
  errorMessage: string | null
}
