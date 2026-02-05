/**
 * Expert Detail Panel - Shows full expert details with source traceability
 * 
 * Displays:
 * - All expert fields with their current values
 * - Source attribution for each field (which email, date, network)
 * - Exact excerpts from source emails
 * - History of field changes over time
 * - User edits clearly labeled
 */

import { useState } from 'react'
import { Mail, Calendar, Building, User, Briefcase, ChevronDown, ChevronRight, History, Edit3, FileText, Sparkles } from 'lucide-react'
import { useExpertDetails } from './api'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import type { Expert, SourceWithProvenance, UserEdit } from './types'

interface ExpertDetailPanelProps {
  expertId: string | null
  expert?: Expert | null
  open: boolean
  onClose: () => void
}

export function ExpertDetailPanel({ expertId, expert, open, onClose }: ExpertDetailPanelProps) {
  const { data: expertDetails, isLoading } = useExpertDetails(expertId)
  
  // Merge basic expert data with details if available
  const fullExpert = expertDetails || expert
  const sources = expertDetails?.sources || []
  const userEdits = expertDetails?.userEdits || []

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <User className="w-5 h-5 text-purple-600" />
            Expert Details
          </DialogTitle>
        </DialogHeader>

        {isLoading ? (
          <div className="py-8 text-center text-gray-500">
            Loading expert details...
          </div>
        ) : !fullExpert ? (
          <div className="py-8 text-center text-gray-500">
            Expert not found
          </div>
        ) : (
          <div className="space-y-6 py-4">
            {/* Header Section */}
            <div className="border-b pb-4">
              <h2 className="text-xl font-semibold">{fullExpert.canonicalName}</h2>
              <div className="flex items-center gap-4 mt-2 text-gray-600">
                {fullExpert.canonicalEmployer && (
                  <span className="flex items-center gap-1">
                    <Building className="w-4 h-4" />
                    {fullExpert.canonicalEmployer}
                  </span>
                )}
                {fullExpert.canonicalTitle && (
                  <span className="flex items-center gap-1">
                    <Briefcase className="w-4 h-4" />
                    {fullExpert.canonicalTitle}
                  </span>
                )}
              </div>
              
            </div>

            {/* AI Screening Section - Styled card format */}
            {fullExpert.aiScreeningGrade && (
              <AIScreeningCard expert={fullExpert} />
            )}

            {/* Field Details with Source Attribution */}
            <div className="space-y-4">
              <h3 className="font-medium text-gray-700 flex items-center gap-2">
                <FileText className="w-4 h-4" />
                Expert Profile with Sources
              </h3>
              
              <FieldWithSource
                fieldName="Name"
                currentValue={fullExpert.canonicalName}
                sources={sources}
                userEdits={userEdits}
                sourceField="extractedName"
              />
              
              <FieldWithSource
                fieldName="Employer"
                currentValue={fullExpert.canonicalEmployer}
                sources={sources}
                userEdits={userEdits}
                sourceField="extractedEmployer"
              />
              
              <FieldWithSource
                fieldName="Title"
                currentValue={fullExpert.canonicalTitle}
                sources={sources}
                userEdits={userEdits}
                sourceField="extractedTitle"
              />
              
              <FieldWithSource
                fieldName="Bio / Background"
                currentValue={null}
                sources={sources}
                userEdits={userEdits}
                sourceField="extractedBio"
                showAllSources
              />
              
              <FieldWithSource
                fieldName="Screener Responses"
                currentValue={null}
                sources={sources}
                userEdits={userEdits}
                sourceField="extractedScreener"
                showAllSources
              />
              
              <FieldWithSource
                fieldName="Availability"
                currentValue={null}
                sources={sources}
                userEdits={userEdits}
                sourceField="extractedAvailability"
                showAllSources
              />
            </div>

            {/* Source Email History */}
            {sources.length > 0 && (
              <div className="space-y-3 border-t pt-4">
                <h3 className="font-medium text-gray-700 flex items-center gap-2">
                  <Mail className="w-4 h-4" />
                  Source Emails ({sources.length})
                </h3>
                
                <div className="space-y-2">
                  {sources.map((source, idx) => (
                    <SourceEmailCard key={source.id} source={source} index={idx + 1} />
                  ))}
                </div>
              </div>
            )}

            {/* User Edit History */}
            {userEdits.length > 0 && (
              <div className="space-y-3 border-t pt-4">
                <h3 className="font-medium text-gray-700 flex items-center gap-2">
                  <Edit3 className="w-4 h-4" />
                  Manual Edits ({userEdits.length})
                </h3>
                
                <div className="space-y-2">
                  {userEdits.map((edit) => (
                    <UserEditCard key={edit.id} edit={edit} />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        <div className="flex justify-end pt-4 border-t">
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}

/**
 * Field with Source Attribution
 */
function FieldWithSource({
  fieldName,
  currentValue,
  sources,
  userEdits,
  sourceField,
  showAllSources = false,
}: {
  fieldName: string
  currentValue: string | null
  sources: SourceWithProvenance[]
  userEdits: UserEdit[]
  sourceField: string
  showAllSources?: boolean
}) {
  const [expanded, setExpanded] = useState(false)
  
  // Find sources that have this field
  const sourcesWithField = sources.filter(s => {
    const value = (s as any)[sourceField]
    return value !== null && value !== undefined && value !== ''
  })
  
  // Check if user edited this field (map field names)
  const fieldNameMap: Record<string, string> = {
    'extractedName': 'canonicalName',
    'extractedEmployer': 'canonicalEmployer',
    'extractedTitle': 'canonicalTitle',
  }
  const dbFieldName = fieldNameMap[sourceField] || sourceField
  const userEdit = userEdits.find(e => e.fieldName === dbFieldName)
  
  // Get the most recent source value
  const latestSource = sourcesWithField[0]
  const latestValue = latestSource ? (latestSource as any)[sourceField] : null
  
  // Get provenance for this field from the latest source
  const provenanceList = latestSource?.provenance?.filter(p => 
    p.fieldName.toLowerCase().includes(sourceField.replace('extracted', '').toLowerCase())
  ) || []
  
  const displayValue = currentValue || latestValue || '—'
  const hasHistory = sourcesWithField.length > 1

  if (sourcesWithField.length === 0 && !currentValue && !showAllSources) {
    return null
  }

  return (
    <div className="bg-gray-50 rounded-lg p-3">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-gray-700">{fieldName}</span>
            {userEdit && (
              <Badge variant="outline" className="text-xs bg-blue-50 border-blue-200 text-blue-700">
                <Edit3 className="w-3 h-3 mr-1" />
                User edited
              </Badge>
            )}
            {hasHistory && (
              <button
                onClick={() => setExpanded(!expanded)}
                className="text-xs text-purple-600 hover:text-purple-700 flex items-center gap-1"
              >
                <History className="w-3 h-3" />
                {sourcesWithField.length} sources
                {expanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
              </button>
            )}
          </div>
          
          <div className="mt-1 text-sm">
            {typeof displayValue === 'string' && displayValue.length > 200 
              ? displayValue.substring(0, 200) + '...'
              : displayValue
            }
          </div>
          
          {/* Source attribution for current value */}
          {latestSource && !userEdit && (
            <div className="mt-2 text-xs text-gray-500 flex items-center gap-2">
              <Mail className="w-3 h-3" />
              <span>
                {latestSource.email_network || latestSource.network || 'Unknown network'}
              </span>
              {latestSource.email_date && (
                <>
                  <span>•</span>
                  <Calendar className="w-3 h-3" />
                  <span>{new Date(latestSource.email_date).toLocaleDateString()}</span>
                </>
              )}
            </div>
          )}
          
          {/* Excerpt if available */}
          {provenanceList.length > 0 && provenanceList[0].excerptText && (
            <div className="mt-2 text-xs bg-white border-l-2 border-purple-300 pl-2 py-1 text-gray-600 italic">
              "{provenanceList[0].excerptText}"
            </div>
          )}
        </div>
      </div>
      
      {/* Expanded history */}
      {expanded && hasHistory && (
        <div className="mt-3 pt-3 border-t space-y-2">
          <p className="text-xs font-medium text-gray-500">Value History:</p>
          {sourcesWithField.map((source, idx) => {
            const value = (source as any)[sourceField]
            const prov = source.provenance?.find(p => 
              p.fieldName.toLowerCase().includes(sourceField.replace('extracted', '').toLowerCase())
            )
            
            return (
              <div key={source.id} className={`text-xs p-2 rounded ${idx === 0 ? 'bg-purple-50 border border-purple-100' : 'bg-white border'}`}>
                <div className="flex items-center gap-2 text-gray-500 mb-1">
                  {idx === 0 && <Badge variant="secondary" className="text-xs">Current</Badge>}
                  <span>{source.email_network || source.network}</span>
                  <span>•</span>
                  <span>{source.email_date ? new Date(source.email_date).toLocaleDateString() : 'Unknown date'}</span>
                </div>
                <div className="text-gray-700">
                  {typeof value === 'string' && value.length > 100 
                    ? value.substring(0, 100) + '...'
                    : value
                  }
                </div>
                {prov?.excerptText && (
                  <div className="mt-1 text-gray-500 italic">
                    "{prov.excerptText}"
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

/**
 * Source Email Card
 */
function SourceEmailCard({ source, index }: { source: SourceWithProvenance; index: number }) {
  const [expanded, setExpanded] = useState(false)
  
  return (
    <div className="border rounded-lg p-3 bg-white">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left flex items-center justify-between"
      >
        <div className="flex items-center gap-3">
          <div className="w-6 h-6 rounded-full bg-gray-100 flex items-center justify-center text-xs font-medium text-gray-600">
            {index}
          </div>
          <div>
            <div className="font-medium text-sm">
              {source.email_network || source.network || 'Unknown network'}
            </div>
            <div className="text-xs text-gray-500">
              {source.email_date 
                ? new Date(source.email_date).toLocaleDateString() 
                : new Date(source.createdAt).toLocaleDateString()
              }
            </div>
          </div>
        </div>
        {expanded ? <ChevronDown className="w-4 h-4 text-gray-400" /> : <ChevronRight className="w-4 h-4 text-gray-400" />}
      </button>
      
      {expanded && (
        <div className="mt-3 pt-3 border-t">
          {/* Fields extracted from this source */}
          <div className="space-y-2 text-xs">
            {source.extractedName && (
              <div><span className="font-medium">Name:</span> {source.extractedName}</div>
            )}
            {source.extractedEmployer && (
              <div><span className="font-medium">Employer:</span> {source.extractedEmployer}</div>
            )}
            {source.extractedTitle && (
              <div><span className="font-medium">Title:</span> {source.extractedTitle}</div>
            )}
            {source.extractedBio && (
              <div>
                <span className="font-medium">Bio:</span>
                <div className="mt-1 text-gray-600 whitespace-pre-wrap">
                  {source.extractedBio.length > 300 
                    ? source.extractedBio.substring(0, 300) + '...' 
                    : source.extractedBio
                  }
                </div>
              </div>
            )}
            {source.extractedScreener && (
              <div>
                <span className="font-medium">Screener:</span>
                <div className="mt-1 text-gray-600 whitespace-pre-wrap">
                  {source.extractedScreener.length > 300 
                    ? source.extractedScreener.substring(0, 300) + '...' 
                    : source.extractedScreener
                  }
                </div>
              </div>
            )}
          </div>
          
          {/* Provenance details */}
          {source.provenance && source.provenance.length > 0 && (
            <div className="mt-3 pt-2 border-t">
              <p className="text-xs font-medium text-gray-500 mb-2">Extracted Fields:</p>
              <div className="space-y-1">
                {source.provenance.map((prov) => (
                  <div key={prov.id} className="text-xs bg-gray-50 rounded p-2">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium">{prov.fieldName}</span>
                      <Badge variant="outline" className="text-xs">
                        {prov.confidence} confidence
                      </Badge>
                    </div>
                    {prov.excerptText && (
                      <div className="text-gray-600 italic">"{prov.excerptText}"</div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

/**
 * AI Screening Card - Styled display for Smart Fit Assessment
 */
function AIScreeningCard({ expert }: { expert: any }) {
  // Parse missing info if it's a JSON string
  const missingInfo = expert.aiScreeningMissingInfo 
    ? (typeof expert.aiScreeningMissingInfo === 'string' 
        ? JSON.parse(expert.aiScreeningMissingInfo) 
        : expert.aiScreeningMissingInfo)
    : null

  const gradeColor = expert.aiScreeningGrade === 'strong' 
    ? 'text-green-600 bg-green-50 border-green-200' 
    : expert.aiScreeningGrade === 'mixed' 
      ? 'text-yellow-600 bg-yellow-50 border-yellow-200' 
      : 'text-red-600 bg-red-50 border-red-200'

  return (
    <div className="space-y-3">
      <h3 className="font-medium text-gray-700 flex items-center gap-2">
        <Sparkles className="w-4 h-4 text-purple-600" />
        Smart Fit Assessment
      </h3>
      
      {/* Grade and Score Card */}
      <div className={`rounded-lg border p-4 ${gradeColor}`}>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium opacity-70">Overall Grade</p>
            <p className="text-2xl font-bold capitalize">{expert.aiScreeningGrade}</p>
          </div>
          <div className="text-right">
            <p className="text-sm font-medium opacity-70">Score</p>
            <p className="text-3xl font-bold">{expert.aiScreeningScore}</p>
          </div>
        </div>
        {expert.aiScreeningConfidence && (
          <p className="text-sm mt-2 opacity-70">
            Confidence: <span className="capitalize">{expert.aiScreeningConfidence}</span>
          </p>
        )}
      </div>

      {/* Rationale */}
      {expert.aiScreeningRationale && (
        <div>
          <p className="text-sm font-medium text-gray-700 mb-1">Assessment Rationale</p>
          <p className="text-sm text-gray-600 bg-gray-50 rounded-lg p-3">
            {expert.aiScreeningRationale}
          </p>
        </div>
      )}

      {/* Missing Info */}
      {missingInfo && missingInfo.length > 0 && (
        <div>
          <p className="text-sm font-medium text-amber-700 mb-1 flex items-center gap-1">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            Missing Information
          </p>
          <ul className="text-sm text-amber-600 bg-amber-50 rounded-lg p-3 list-disc list-inside">
            {missingInfo.map((item: string, index: number) => (
              <li key={index}>{item}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

/**
 * User Edit Card
 */
function UserEditCard({ edit }: { edit: UserEdit }) {
  const previousValue = edit.previousValueJson ? JSON.parse(edit.previousValueJson) : null
  const newValue = JSON.parse(edit.userValueJson)
  
  return (
    <div className="border border-blue-100 bg-blue-50 rounded-lg p-3">
      <div className="flex items-center gap-2 mb-2">
        <Edit3 className="w-4 h-4 text-blue-600" />
        <span className="font-medium text-sm text-blue-800">{edit.fieldName}</span>
        <span className="text-xs text-blue-600">
          {new Date(edit.createdAt).toLocaleDateString()}
        </span>
      </div>
      <div className="text-sm space-y-1">
        {previousValue && (
          <div className="text-gray-500">
            <span className="font-medium">Was:</span> {String(previousValue)}
          </div>
        )}
        <div className="text-blue-800">
          <span className="font-medium">Changed to:</span> {String(newValue)}
        </div>
      </div>
    </div>
  )
}
